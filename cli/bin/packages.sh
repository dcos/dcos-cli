#!/bin/bash -e

echo "Building wheel..."
python setup.py bdist_wheel

echo "Building egg..."
python setup.py sdist

