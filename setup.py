import os
from setuptools import setup, find_packages


project_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(project_dir, 'version.txt')) as f:
    version = f.read().rstrip()

# We allow commented lines in this file
with open(os.path.join(project_dir, 'requirements.txt')) as f:
    requirements = [line.rstrip('\n') for line in f if not line.startswith('#')]


setup(
    name='bouncerscript',
    version=version,
    description='TaskCluster Bouncer Script',
    author='Mozilla Release Engineering',
    author_email='release+python@mozilla.com',
    url='https://github.com/mozilla-releng/bouncerscript',
    packages=find_packages(),
    package_data={
        "bouncerscript": ["data/*"],
    },
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'bouncerscript = bouncerscript.script:main',
        ],
    },
    license='MPL2',
    install_requires=requirements,
    classifiers=(
        'Programming Language :: Python :: 3.5',
    ),
)
