import os

from setuptools import find_packages, setup

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

install_requires = ["arrow", "mar", "scriptworker", "taskcluster", "mohawk", "winsign", "macholib"]

setup(
    name="signingscript",
    version=version,
    description="TaskCluster Signing Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/signingscript",
    package_data={"signingscript": ["data/*"]},
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["signingscript = signingscript.script:main"]},
    license="MPL2",
    install_requires=install_requires,
)
