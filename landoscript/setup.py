# noqa: D100
from setuptools import find_packages, setup

setup(
    name="landoscript",
    # never changes
    version="1.0",
    description="Landoscript scriptworker",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/scriptworker-scripts",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    entry_points={"console_scripts": ["landoscript = landoscript.script:main"]},
    python_requires=">=3.11",
    license="MPL2",
)
