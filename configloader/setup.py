# noqa: D100
import os

from setuptools import find_packages, setup

project_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(project_dir, "version.txt")) as f:
    version = f.read().rstrip()

# We allow commented lines in this file
with open(os.path.join(project_dir, "requirements/base.in")) as f:
    requirements = [line.rstrip("\n") for line in f if not line.startswith("#")]


setup(
    name="configloader",
    version=version,
    description="Config loader",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/scriptworker-scripts",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["configloader = configloader.script:main"]},
    license="MPL2",
    install_requires=requirements,
    classifiers=("Programming Language :: Python :: 3.7", "Programming Language :: Python :: 3.8"),
)
