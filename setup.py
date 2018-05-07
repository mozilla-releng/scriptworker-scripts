# noqa: D100
import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

setup(
    name="addonscript",
    version=version,
    description="Script to submit unsigned addons to AMO and get signed copies back",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/addonscript",
    packages=find_packages(),
    package_data={"addonscript": ["data/*"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "addonscript = addonscript.script:main",
        ],
    },
    license="MPL2",
    install_requires=[
        "scriptworker",
        "python-jose",
    ],
)
