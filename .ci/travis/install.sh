#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == 'Darwin' ]]; then
    brew update
    brew install openssl readline
    brew outdated pyenv || brew upgrade pyenv
    brew install pyenv-virtualenv

    if which pyenv > /dev/null; then eval "$(pyenv init -)"; fi
    if which pyenv > /dev/null; then eval "$(pyenv init -)"; fi

    case "${PYVER}" in
        py27)
            pyenv install 2.7.10
            pyenv virtualenv 2.7.10 conan
            ;;
        py37)
            pyenv install 3.7.1
            pyenv virtualenv 3.7.1 conan
            ;;

    esac
    pyenv rehash
    pyenv activate conan

    python --version
else
    sudo apt-get update
    sudo apt-get install gcc-multilib g++-multilib
fi

pip install -r cpt/requirements.txt
pip install -r cpt/requirements_test.txt
