import os

from setuptools import find_packages, setup

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "requirements", "base.in")) as f:
    install_requires = ["scriptworker_client"] + f.readlines()

setup(
    name="notarization_poller",
    version=version,
    description="TaskCluster Notarization Poller",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/scriptworker-scripts/tree/master/notarization_poller/",
    packages=find_packages("src"),
    package_data={"notarization_poller": ["data/*"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["notarization_poller = notarization_poller.worker:main"]},
    license="MPL2",
    install_requires=install_requires,
)
