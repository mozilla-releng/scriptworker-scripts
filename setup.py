import os
from setuptools import setup, find_packages


project_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(project_dir, 'version.txt')) as f:
    version = f.read().rstrip()

# We're using a pip8 style requirements file, which allows us to embed hashes
# of the packages in it. However, setuptools doesn't support parsing this type
# of file, so we need to strip those out before passing the requirements along
# to it.
with open(os.path.join(project_dir, 'requirements.txt')) as f:
    requirements = [line.split()[0] for line in f if not line.startswith('#')]


setup(
    name='pushapkscript',
    version=version,
    description='TaskCluster Push APK Worker',
    author='Mozilla Release Engineering',
    author_email='release+python@mozilla.com',
    # TODO update Github URL once repo has been renamed
    url='https://github.com/mozilla-releng/pushapkworker',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'pushapkscript = pushapkscript.script:main',
        ],
    },
    license='MPL2',
    install_requires=requirements,
    classifiers=(
        'Programming Language :: Python :: 3.5',
    ),
)
