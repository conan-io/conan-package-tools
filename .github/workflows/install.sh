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
            pyenv install 2.7.16
            pyenv virtualenv 2.7.16 conan
            ;;
        py37)
            pyenv install 3.7.13
            pyenv virtualenv 3.7.13 conan
            ;;

    esac
    pyenv rehash
    pyenv activate conan

    python --version
else
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends gcc-multilib g++-multilib selinux-basics
fi

pip install -U pip
pip install -r cpt/requirements.txt
pip install -r cpt/requirements_test.txt
