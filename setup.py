import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

setup(
    name="applescript",
    version=version,
    description="TaskCluster Apple Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/escapewindow/applescript",
    packages=find_packages(),
    package_data={"applescript": ["data/*"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "applescript = applescript.script:main",
        ],
    },
    license="MPL2",
    install_requires=[
        "scriptworker",
    ],
)
