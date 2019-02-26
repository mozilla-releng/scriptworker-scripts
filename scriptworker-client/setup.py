import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

setup(
    name="scriptworker-client",
    version=version,
    description="Scriptworker *script shared code",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/escapewindow/scriptworker-scripts/tree/master/scriptworker-client",
    packages=find_packages(),
    include_package_data=False,
    zip_safe=True,
    license="MPL2",
    install_requires=[
    ],
)
