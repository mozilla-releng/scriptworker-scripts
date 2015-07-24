from setuptools import setup

setup(
    name="signingworker",
    version="0.4",
    description="TaskCluster Signing Worker",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla/signingworker",
    packages=["signingworker"],
    package_data={"signingworker": ["data/*.json"]},
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "signing-worker = signingworker.consumer:main",
        ],
    },
    # Not zip safe because we have data files in the package
    zip_safe=False,
    license="MPL2",
    install_requires=[
        "arrow",
        "configman",
        "jsonschema",
        "kombu",
        "redo",
        "requests==2.4.3",  # Because taskcluster hard pins this version...
        "sh",
        "taskcluster>=0.0.16",
    ],
)
