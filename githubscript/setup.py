import os

from setuptools import find_packages, setup

project_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(project_dir, "version.txt")) as f:
    version = f.read().rstrip()

# We allow commented lines in this file
with open(os.path.join(project_dir, "requirements/base.in")) as f:
    requirements = [line.rstrip("\n") for line in f if not line.startswith("#")]
    install_requires = ["scriptworker_client"] + requirements

with open(os.path.join(project_dir, "README.md")) as f:
    long_description = f.read()


setup(
    name="githubscript",
    version=version,
    description="Taskcluster worker in charge of updating Github and notably Github Releases",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/scriptworker-scripts/tree/master/githubscript",
    packages=find_packages("src"),
    package_data={"githubscript": ["data/*"]},
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["githubscript = githubscript.script:main"]},
    license="MPL2",
    install_requires=install_requires,
    classifiers=["Programming Language :: Python :: 3.7", "Programming Language :: Python :: 3.8"],
)
