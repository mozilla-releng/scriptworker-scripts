import configparser
import logging
import xml.etree.ElementTree
import zipfile

from scriptworker_client.exceptions import TaskVerificationError

log = logging.getLogger(__name__)


def verify_msix(file_path):
    """
    - is file_path a zip file?
    - is the zip file valid?
    - does the zip file contain an msix manifest?
      - does the msix manifest have an Identity element?
    - does the zip file contain a Firefox application.ini?
      - does application.ini contain some expected elements?
    """

    def _readline_generator(fp):
        line = fp.readline().decode()
        while line:
            yield line
            line = fp.readline().decode()

    MSIX_MANIFEST_FILE = "AppxManifest.xml"
    APPLICATION_INI_FILE = "application.ini"
    ns = {"win10": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
    with zipfile.ZipFile(file_path) as zf:
        if zf.testzip() is not None:
            raise TaskVerificationError(f"{file_path} is not a valid zip file")
        with zf.open(MSIX_MANIFEST_FILE) as f:
            tree = xml.etree.ElementTree.parse(f)
            root = tree.getroot()
            id = root.find("win10:Identity", ns)
            archive_version = id.attrib["Version"]
            log.info(f"Archive version: {archive_version}")
        app_manifest = [n for n in zf.namelist() if n.endswith(APPLICATION_INI_FILE)]
        if len(app_manifest) != 1:
            raise TaskVerificationError(f"{APPLICATION_INI_FILE} not found or not unique")
        app_manifest = app_manifest[0]
        with zf.open(app_manifest) as f:
            config = configparser.ConfigParser()
            config.read_file(_readline_generator(f))
            version = config.get("App", "Version", fallback="unknown")
            build_id = config.get("App", "BuildId", fallback="unknown")
            code_name = config.get("App", "CodeName", fallback=config.get("App", "Name", fallback="unknown"))
            log.info(f"Firefox version: {version}")
            log.info(f"Firefox build id: {build_id}")
            log.info(f"Firefox code name: {code_name}")
    return True
