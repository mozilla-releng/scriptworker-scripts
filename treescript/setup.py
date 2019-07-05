# noqa: D100
import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "requirements", "base.in")
) as f:
    install_requires = f.readlines()

setup(
    name="treescript",
    version=version,
    description="Tree Modifying Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/scriptworker-scripts",
    packages=find_packages(),
    package_data={"treescript": ["data/*", "py2/*"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "treescript = treescript.script:main",
        ],
    },
    license="MPL2",
    install_requires=install_requires,
)
