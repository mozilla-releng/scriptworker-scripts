import os
from setuptools import setup, find_packages

with open("requirements/base.in") as f:
    install_requires = f.readlines()


def get_version():
    PATH = os.path.join(os.path.dirname(__file__), "beetmoverscript/_version.py")
    d = {}
    with open(PATH) as filehandle:
        exec(filehandle.read(), d)
    return d['__version__']


setup(
    name="beetmoverscript",
    version=get_version(),
    description="TaskCluster Beetmover Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/beetmoverscript/",
    packages=find_packages(),
    package_data={
        "beetmoverscript": ["data/*", "templates/*"],
    },
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "beetmoverscript = beetmoverscript.script:main",
        ],
    },
    license="MPL2",
    install_requires=install_requires,
    classifiers=(
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ),
)
