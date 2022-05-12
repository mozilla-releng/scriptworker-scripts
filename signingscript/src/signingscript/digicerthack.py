"""Work around DigiCert timestamp signatures missing a trust path on Windows 7."""
import io
import logging
import pathlib
import tempfile

from pyasn1.codec.der.decoder import decode as der_decode
from pyasn1.codec.der.encoder import encode as der_encode
from pyasn1_modules.pem import readPemFromFile
from pyasn1_modules.rfc2315 import ContentInfo, ExtendedCertificateOrCertificate
from pyasn1_modules.rfc5280 import X520CommonName, id_at_commonName
from winsign import asn1, osslsigncode, pefile

log = logging.getLogger(__name__)

digicert_cross_sign = """\
-----BEGIN CERTIFICATE-----
MIIFqTCCBJGgAwIBAgIQAmpTRVzHABL6I856gPheRzANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBD
QTAeFw0xMzA3MDExMjAwMDBaFw0yMzEwMjIxMjAwMDBaMGIxCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xITAfBgNVBAMTGERpZ2lDZXJ0IFRydXN0ZWQgUm9vdCBHNDCCAiIwDQYJKoZI
hvcNAQEBBQADggIPADCCAgoCggIBAL/mkHNo3rvkXUo8MCIwaTPswqclLskhPfKK
2FnC4SmnPVirdprNrnsbhA3EMB/zG6Q4FutWxpdtHauyefLKEdLkX9YFPFIPUh/G
nhWlfr6fqVcWWVVyr2iTcMKyunWZanMylNEQRBAu34LzB4TmdDttceItDBvuINXJ
IB1jKS3O7F5OyJP4IWGbNOsFxl7sWxq868nPzaw0QF+xembud8hIqGZXV59UWI4M
K7dPpzDZVu7Ke13jrclPXuU15zHL2pNe3I6PgNq2kZhAkHnDeMe2scS1ahg4AxCN
2NQ3pC4FfYj1gj4QkXCrVYJBMtfbBHMqbpEBfCFM1LyuGwN1XXhm2ToxRJozQL8I
11pJpMLmqaBn3aQnvKFPObURWBf3JFxGj2T3wWmIdph2PVldQnaHiZdpekjw4KIS
G2aadMreSx7nDmOu5tTvkpI6nj3cAORFJYm2mkQZK37AlLTSYW3rM9nF30sEAMx9
HJXDj/chsrIRt7t/8tWMcCxBYKqxYxhElRp2Yn72gLD76GSmM9GJB+G9t+ZDpBi4
pncB4Q+UDCEdslQpJYls5Q5SUUd0viastkF13nqsX40/ybzTQRESW+UQUOsxxcpy
FiIJ33xMdT9j7CFfxCBRa2+xq4aLT8LWRV+dIPyhHsXAj6KxfgommfXkaS+YHS31
2amyHeUbAgMBAAGjggFaMIIBVjASBgNVHRMBAf8ECDAGAQH/AgEBMA4GA1UdDwEB
/wQEAwIBhjA0BggrBgEFBQcBAQQoMCYwJAYIKwYBBQUHMAGGGGh0dHA6Ly9vY3Nw
LmRpZ2ljZXJ0LmNvbTB7BgNVHR8EdDByMDegNaAzhjFodHRwOi8vY3JsNC5kaWdp
Y2VydC5jb20vRGlnaUNlcnRHbG9iYWxSb290Q0EuY3JsMDegNaAzhjFodHRwOi8v
Y3JsMy5kaWdpY2VydC5jb20vRGlnaUNlcnRHbG9iYWxSb290Q0EuY3JsMD0GA1Ud
IAQ2MDQwMgYEVR0gADAqMCgGCCsGAQUFBwIBFhxodHRwczovL3d3dy5kaWdpY2Vy
dC5jb20vQ1BTMB0GA1UdDgQWBBTs1+OC0nFdZEzfLmc/57qYrhwPTzAfBgNVHSME
GDAWgBQD3lA1VtFMu2bwo+IbG8OXsj3RVTANBgkqhkiG9w0BAQsFAAOCAQEATX3N
y6uAw4zUl+/AucL89ywo2jUgqiSUZxRK5rHg/OBvM9q9kh99ZJSVlUpxw7s3G6Iv
OcFh1yCvwkYhzOnHpVlJ2jZA+MuIjufnAr7jJMj7iw0HiW9Jair1lplPO9z6JSL/
ifT+C2xl9gkv9bwG2j0u/BLGvLJApOFj/S/HoVg33gQJeqFZwmZER4sxGCcj26xx
JvjZsepf4cP2U2n+CQZoA1M5rbuprg/8SgAmgINP7Yl7GRe/TlyUOKsx9klkn9Uy
6QGeHZIvoQ1dylT6hXwWeiagZGPE1wlpHs+8ah7WhSG0a+P1sn0QSopUfZyV59Ow
Sx2Q1FL4934+qkh0Hg==
-----END CERTIFICATE-----
"""


def _issuer_commonname(cert):
    """Extract the commonName attribute from the certificate's issuer.

    Args:
        cert: input certificate, wrapped in a ASN.1 ExtendedCertificateOrCertificate object

    Returns:
        str: the certificate issuer's commonName or None
    """
    for rdn in cert["certificate"]["tbsCertificate"]["issuer"][0]:
        if rdn[0]["type"] == id_at_commonName:
            cn, _ = der_decode(rdn[0]["value"], X520CommonName())
            return str(cn.getComponent())


def add_cert_to_signature(sig):
    """Mangle signature by adding a DigiCert cross-certificate.

    Args:
        sig(bytes): binary signature, corresponding to an encoded ContentInfo object

    Returns:
        bytes: a new signature, which may be the same as sig if the extra certificate is not needed
    """
    sd = asn1.get_signeddata(sig)
    issuers = [_issuer_commonname(cert) for cert in sd["certificates"]]
    if "DigiCert Trusted Root G4" not in issuers or "DigiCert Global Root CA" in issuers:
        log.info("No need to add_cert_to_signature, skipping...")
        return sig
    log.info("Adding cert to signature...")
    crosscert_der = readPemFromFile(io.StringIO(digicert_cross_sign))
    sd["certificates"].append(der_decode(crosscert_der, ExtendedCertificateOrCertificate())[0])
    ci = ContentInfo()
    ci["contentType"] = asn1.id_signedData
    ci["content"] = sd
    return der_encode(ci)


def add_cert_to_signed_file(old, new, cafile, timestampfile):
    """Add DigiCert cross-certificate to a signed binary if necessary.

    Args:
        old(str): path to the signed file we want to mangle
        new(str): output path; must not exist
        cafile(str): path to certificate bundle to verify the signature
        timestampfile(str): path to certificate bundle to verify the timestamp counter signature

    Raises:
        OSError: osslsigncode returned with non-zero status

    Returns:
        None on success
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        signature_path = tmpdir / "old-signature"
        log.info(f"Extracting signature from {old}...")
        osslsigncode.extract_signature(old, signature_path)
        unsigned_path = tmpdir / "unsigned"
        cmd = ["remove-signature", "-in", old, "-out", unsigned_path]
        osslsigncode.osslsigncode(cmd)
        if pefile.is_pefile(old):
            pefile_cert = pefile.certificate.parse(signature_path.read_bytes())
            sig = pefile_cert.data
        else:
            sig = signature_path.read_bytes()
        newsig = add_cert_to_signature(sig)
        log.info(f"Writing signature to {new}...")
        osslsigncode.write_signature(unsigned_path, new, newsig, None, cafile, timestampfile)


if __name__ == "__main__":
    import sys

    old = sys.argv[1]
    new = sys.argv[2]
    add_cert_to_signed_file(old, new, "/usr/lib/ssl/certs/ca-certificates.crt", "/usr/lib/ssl/certs/ca-certificates.crt")
