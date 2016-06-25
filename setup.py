from setuptools import setup, find_packages

setup(
    name="signingscript",
    version="0.1.0",
    description="TaskCluster Signing Script",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/escapewindow/signingscript",
    packages=find_packages(),
    package_data={"signingscript": ["data/*.json"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "signingscript = signingscript.script:main",
        ],
    },
    license="MPL2",
    install_requires=[
        "arrow==0.8.0",
        "python-jose==0.7.0",
        # "scriptworker==0.1.2",
        "scriptworker",
        "signtool==1.0.8",
        "taskcluster==0.3.3",
    ],
)
