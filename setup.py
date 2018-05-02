import os
from setuptools import setup, find_packages


def get_version():
    PATH = os.path.join(os.path.dirname(__file__), "balrogscript/_version.py")
    d = {}
    with open(PATH) as filehandle:
        exec(filehandle.read(), d)
    return d['__version__']


setup(
    name="balrogscript",
    version=get_version(),
    description="TaskCluster Balrog Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/balrogscript",
    packages=find_packages(),
    package_data={
        "balrogscript": ["data/*"],
        "": ["version.json"],
    },
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "balrogscript = balrogscript.script:main",
        ],
    },
    license="MPL2",
    install_requires=[
        "arrow",
        "cryptography",
        "enum34",
        "idna",
        "ipaddress",
        "jsonschema",
        "mar",
        "pyasn1",
        "six",
    ],
    classifiers=(
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
    ),
)
