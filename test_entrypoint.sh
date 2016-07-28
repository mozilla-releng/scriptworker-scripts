#!/bin/bash -xe


source py2/bin/activate
pip install nose

mkdir /app/work
cd /app/work
nosetests ../bin -v

#pip install tox
#tox bin