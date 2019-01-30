#!/bin/bash

set -e
set -x

if [ "$TRAVIS_OS_NAME" == "linux" ]; then
    sudo apt-get update
    sudo apt-get install gcc-multilib g++-multilib
fi

pip install -r cpt/requirements.txt
pip install -r cpt/requirements_test.txt
