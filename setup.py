import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "requirements/base.in")
) as f:
    install_requires = f.readlines()

setup(
    name="signingscript",
    version=version,
    description="TaskCluster Signing Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/signingscript",
    packages=find_packages(),
    package_data={"signingscript": ["data/*"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["signingscript = signingscript.script:main"]},
    license="MPL2",
    install_requires=install_requires,
)
