#!/bin/bash


source /app/py2/bin/activate
pip install nose

mkdir /app/bin/work
cd /app/bin/work
nosetests /app/bin -v
