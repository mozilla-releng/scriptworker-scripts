import os

from setuptools import find_packages, setup

with open("requirements/base.in") as f:
    install_requires = f.readlines()

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

setup(
    name="beetmoverscript",
    version=version,
    description="TaskCluster Beetmover Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/beetmoverscript/",
    packages=find_packages("src"),
    package_data={"beetmoverscript": ["data/*", "templates/*"]},
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["beetmoverscript = beetmoverscript.script:main"]},
    license="MPL2",
    install_requires=install_requires,
    classifiers=[
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
