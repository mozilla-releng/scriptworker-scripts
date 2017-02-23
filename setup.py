import json
import os
from setuptools import setup, find_packages

PATH = os.path.join(os.path.dirname(__file__), "version.json")
with open(PATH) as filehandle:
    VERSION = json.load(filehandle)['version_string']

setup(
    name="beetmoverscript",
    version=VERSION,
    description="TaskCluster Beetmover Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/beetmoverscript/",
    packages=find_packages(),
    package_data={
        "beetmoverscript": ["data/*", "templates/*"],
        "": ["version.json"],
    },
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "beetmoverscript = beetmoverscript.script:main",
        ],
    },
    license="MPL2",
    install_requires=[
        "arrow",
        "scriptworker",
        "taskcluster",
        "boto3",
        "PyYAML",
        "Jinja2",
    ],
    classifiers=(
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
    ),
)
