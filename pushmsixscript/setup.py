import os

from setuptools import find_packages, setup

project_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(project_dir, "version.txt")) as f:
    version = f.read().rstrip()

# We allow commented lines in this file
with open(os.path.join(project_dir, "requirements/base.in")) as f:
    requirements = [line.rstrip("\n") for line in f if not line.startswith("#")]

snapcraft_version = "3.9.1"
requirements = ["snapcraft=={}".format(snapcraft_version) if "snapcraft" in requirement else requirement for requirement in requirements]

setup(
    name="pushmsixscript",
    version=version,
    description="TaskCluster Ship-It Worker",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/pushmsixscript",
    packages=find_packages("src"),
    package_data={"pushmsixscript": ["data/*"]},
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["pushmsixscript = pushmsixscript.script:main"]},
    license="MPL2",
    install_requires=requirements,
    dependency_links=["https://github.com/snapcore/snapcraft/archive/3.10.tar.gz#egg=snapcraft-{}".format(snapcraft_version)],
    classifiers=["Programming Language :: Python :: 3.6", "Programming Language :: Python :: 3.7"],
)
