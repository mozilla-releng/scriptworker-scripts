import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

setup(
    name="balrogscript",
    version=version,
    description="TaskCluster Balrog Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/balrogscript",
    packages=find_packages(),
    package_data={"balrogscript": ["keys/*"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "balrogscript = balrogscript.balrogscript:main",
        ],
    },
    license="MPL2",
    install_requires=[
        "boto",
        "cryptography",
        "enum34",
        "idna",
        "ipaddress",
        "mar",
        "pyasn1",
        "requests",
        "six",
    ],
)
