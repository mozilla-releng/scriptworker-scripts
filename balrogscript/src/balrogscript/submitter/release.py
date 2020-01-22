import re
from urllib.parse import urlunsplit


def getProductDetails(product, appVersion):
    return "https://www.mozilla.org/%%LOCALE%%/%s/%s/releasenotes/" % (product, appVersion)


def getPrettyVersion(version):
    version = re.sub(r"a([0-9]+)$", r" Alpha \1", version)
    version = re.sub(r"b([0-9]+)$", r" Beta \1", version)
    version = re.sub(r"rc([0-9]+)$", r" RC \1", version)
    return version


product_ftp_map = {"fennec": "mobile"}


def product2ftp(product):
    return product_ftp_map.get(product, product)


def makeCandidatesDir(product, version, buildNumber, nightlyDir="candidates", protocol=None, server=None, ftp_root="/pub/"):
    if protocol:
        assert server is not None, "server is required with protocol"

    product = product2ftp(product)
    directory = ftp_root + product + "/" + nightlyDir + "/" + str(version) + "-candidates/build" + str(buildNumber) + "/"

    if protocol:
        return urlunsplit((protocol, server, directory, None, None))
    else:
        return directory


bouncer_platform_map = {"win32": "win", "win64": "win64", "macosx": "osx", "linux": "linux", "linux64": "linux64", "macosx64": "osx"}
# buildbot -> ftp platform mapping
ftp_platform_map = {
    "win32": "win32",
    "win64": "win64",
    "macosx": "mac",
    "linux": "linux-i686",
    "linux64": "linux-x86_64",
    "macosx64": "mac",
    "linux-android": "android",
    "linux-mobile": "linux",
    "macosx-mobile": "macosx",
    "win32-mobile": "win32",
    "android": "android",
    "android-xul": "android-xul",
}
# buildbot -> update platform mapping
update_platform_map = {
    "android": ["Android_arm-eabi-gcc3"],
    "android-api-11": ["Android_arm-eabi-gcc3"],
    "android-api-15": ["Android_arm-eabi-gcc3"],
    "android-api-15-old-id": ["Android_arm-eabi-gcc3"],
    "android-api-16": ["Android_arm-eabi-gcc3"],
    "android-api-16-old-id": ["Android_arm-eabi-gcc3"],
    "android-x86": ["Android_x86-gcc3"],
    "android-x86-old-id": ["Android_x86-gcc3"],
    "android-aarch64": ["Android_aarch64-gcc3"],
    "linux": ["Linux_x86-gcc3"],
    "linux64": ["Linux_x86_64-gcc3"],
    "linux64-asan-reporter": ["Linux_x86_64-gcc3-asan"],
    "macosx64": [
        "Darwin_x86_64-gcc3-u-i386-x86_64",  # The main platofrm
        "Darwin_x86-gcc3-u-i386-x86_64",
        # We don't ship builds with these build targets, but some users
        # modify their builds in a way that has them report like these.
        # See bug 1071576 for details.
        "Darwin_x86-gcc3",
        "Darwin_x86_64-gcc3",
    ],
    "win32": ["WINNT_x86-msvc", "WINNT_x86-msvc-x86", "WINNT_x86-msvc-x64"],
    "win64": ["WINNT_x86_64-msvc", "WINNT_x86_64-msvc-x64"],
    "win64-asan-reporter": ["WINNT_x86_64-msvc-x64-asan"],
    "win64-aarch64": ["WINNT_aarch64-msvc-aarch64"],
}


def buildbot2bouncer(platform):
    return bouncer_platform_map.get(platform, platform)


def buildbot2ftp(platform):
    return ftp_platform_map.get(platform, platform)


def buildbot2updatePlatforms(platform):
    return update_platform_map.get(platform, [platform])
