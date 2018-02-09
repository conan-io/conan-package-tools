# Conan Package Tools [![Build Status](https://travis-ci.org/conan-io/conan-package-tools.svg?branch=master)](https://travis-ci.org/conan-io/conan-package-tools)


## Introduction

This package allows to automate the creation of [conan](https://github.com/conan-io/conan) packages for different configurations.

It eases the integration with CI servers like [TravisCI](https://travis-ci.org/) and [Appveyor](http://www.appveyor.com/), so you can use the
cloud to generate different binary packages for your conan recipe.

Also supports Docker to create packages for different **GCC and Clang** versions.

## Installation

    $ pip install conan_package_tools


Or you can [clone this repository](http://github.com/conan-io/conan-package-tools) and store its location in PYTHONPATH.


## How it works

Using only conan C/C++ package manager (without conan package tools), you can use the `conan create` command to generate, for the same recipe, different binary packages for different configurations.
The easier way to do it is using profiles:

    $ conan create myuser/channel --profile win32
    $ conan create myuser/channel --profile raspi
    $ ...

The profiles can contain, settings, options, environment variables and build_requires. Take a look to the [conan docs](https://docs.conan.io) to know more.

`Conan package tools` allows to declare (or autogenerate) a set of different configurations (different profiles). It will call `conan create` for each one, uploading the generated packages
to a remote (if needed), and using optionally docker images to ease the creation of different binaries for different compiler versions (gcc and clang supported).

### Basic, but not very practical, example

Create a **build.py** file in your recipe repository, and add the following lines:

    from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager(username="myusername")
	    builder.add(settings={"arch": "x86", "build_type": "Debug"},
	                options={}, env_vars={}, build_requires={})
	    builder.add(settings={"arch": "x86_64", "build_type": "Debug"},
	                options={}, env_vars={}, build_requires={})
	    builder.run()

Now we can run the python script, the `ConanMutiPackager` will run the `conan create` command two times, one to generate `x86 Debug` package and
another one for `x86_64 Debug`.


    > python build.py

    ############## CONAN PACKAGE TOOLS ######################

    INFO: ******** RUNNING BUILD **********
    conan create myuser/testing --profile /var/folders/y1/9qybgph50sjg_3sm2_ztlm6dr56zsd/T/tmpz83xXmconan_package_tools_profiles/profile

    [build_requires]
    [settings]
    arch=x86
    build_type=Debug
    [options]
    [scopes]
    [env]

    ...


    ############## CONAN PACKAGE TOOLS ######################

    INFO: ******** RUNNING BUILD **********
    conan create myuser/testing --profile /var/folders/y1/9qybgph50sjg_3sm2_ztlm6dr56zsd/T/tmpMiqSZUconan_package_tools_profiles/profile

    [build_requires]
    [settings]
    arch=x86_64
    build_type=Debug
    [options]
    [scopes]
    [env]


    #########################################################

    ...


If we inspect the local cache we can see that there are two binaries generated for our recipe, in this case the zlib recipe:

    $ conan search zlib/1.2.11@myuser/testing

    Existing packages for recipe zlib/1.2.11@myuser/testing:

    Package_ID: a792eaa8ec188d30441564f5ba593ed5b0136807
        [options]
            shared: False
        [settings]
            arch: x86
            build_type: Debug
            compiler: apple-clang
            compiler.version: 9.0
            os: Macos
        outdated from recipe: False

    Package_ID: e68b263f26a4d7513e28c9cae1673aa0466af777
        [options]
            shared: False
        [settings]
            arch: x86_64
            build_type: Debug
            compiler: apple-clang
            compiler.version: 9.0
            os: Macos
        outdated from recipe: False


Now, we could add new build configurations, but in this case we only want to add Visual Studio configurations and the runtime, but, of course, only if we are on Windows:

    import platform
    from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager(username="myusername")
	    if platform.system() == "Windows":
	        builder.add(settings={"arch": "x86", "build_type": "Debug", "compiler": "Visual Studio", "compiler.version": 14, "compiler.runtime": "MTd"},
	                    options={}, env_vars={}, build_requires={})
	        builder.add(settings={"arch": "x86_64", "build_type": "Release", "compiler": "Visual Studio", "compiler.version": 14, "compiler.runtime": "MT"},
	                    options={}, env_vars={}, build_requires={})
	    else:
	        builder.add(settings={"arch": "x86", "build_type": "Debug"},
	                    options={}, env_vars={}, build_requires={})
	        builder.add(settings={"arch": "x86_64", "build_type": "Debug"},
	                    options={}, env_vars={}, build_requires={})
	    builder.run()

In the previous example, when we are on Windows, we are adding two build configurations:

    - "Visual Studio 14, Debug, MTd runtime"
    - "Visual Studio 14, Release, MT runtime"


We can also adjust the options, environment variables and build_requires:

	from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager(username="myuser")
	    builder.add({"arch": "x86", "build_type": "Release"},
	                {"mypackage:option1": "ON"},
	                {"PATH": "/path/to/custom"},
	                {"*": ["MyBuildPackage/1.0@lasote/testing"]})
        builder.add({"arch": "x86_64", "build_type": "Release"}, {"mypackage:option1": "ON"})
        builder.add({"arch": "x86", "build_type": "Debug"}, {"mypackage:option2": "OFF", "mypackage:shared": True})
	    builder.run()


We could continue adding configurations, but probably you realized that it would be such a tedious task if you want to generate many different configurations
in different operating systems, using different compilers, different compiler versions etc.

## Generating the build configurations automatically

Conan package tools can generate automatically a matrix of build configurations combining  architecture, compiler, compiler.version, compiler.runtime, compiler.libcxx, build_type and
and shared/static options.


    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager()
        builder.add_common_builds()
        builder.run()

If you run the ``python build.py`` command, for instance, in Mac OSX, it will add the following configurations automatically:

```
{'compiler.version': '7.3', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '7.3', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'apple-clang'})
{'compiler.version': '7.3', 'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '7.3', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'apple-clang'})
{'compiler.version': '8.0', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '8.0', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'apple-clang'})
{'compiler.version': '8.0', 'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '8.0', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'apple-clang'})
{'compiler.version': '8.1', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '8.1', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'apple-clang'})
{'compiler.version': '8.1', 'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '8.1', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'apple-clang'})
```

These are all the combinations of arch=x86/x86_64, build_type=Release/Debug for different compiler versions.

But having different apple-clang compiler versions installed in the same machine is not common at all.
We can adjust the compiler versions using a parameter or an environment variable, specially useful for a CI environment:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(apple_clang_versions=["9.0"]) # or declare env var CONAN_APPLE_CLANG_VERSIONS=9.0
        builder.add_common_builds()
        builder.run()

In this case, it will call `conan create` with only this configurations:

```
{'compiler.version': '9.0', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '9.0', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'apple-clang'})
{'compiler.version': '9.0', 'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'apple-clang'})
{'compiler.version': '9.0', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'apple-clang'})
```

You can adjust other constructor parameters to control the build configurations that will be generated:


- **gcc_versions**: Generate only build configurations for the specified gcc versions (Ignored if the current machine is not Linux)
- **visual_versions**: Generate only build configurations for the specified Visual Studio versions (Ignore if the current machine is not Windows)
- **visual_runtimes**: Generate only build configurations for the specified runtimes, (only for Visual Studio)
- **apple_clang_versions**: Generate only build configurations for the specified apple clang versions (Ignored if the current machine is not OSX)
- **archs**: Generate build configurations for the specified architectures, by default, ["x86", "x86_64"].
- **build_types**: Generate build configurations for the specified build_types, by default ["Debug", "Release"].

Or you can adjust environment variables:

- **CONAN_GCC_VERSIONS**
- **CONAN_VISUAL_VERSIONS**
- **CONAN_VISUAL_RUNTIMES**
- **CONAN_APPLE_CLANG_VERSIONS**
- **CONAN_CLANG_VERSIONS**
- **CONAN_ARCHS**
- **CONAN_BUILD_TYPES**

Check the **REFERENCE** section to see all the parameters and **ENVIRONMENT VARIABLES** available.


---
**IMPORTANT!** Both the constructor parameters and the corresponding environment variables ONLY affect when calling `builder.add_common_builds()`.

---


So, if we want to generate packages for ``x86_64`` and ``armv8`` but only for ``Debug`` and ``apple-clang 9.0``:


    $ export CONAN_ARCHS=x86_64,armv8
    $ export CONAN_APPLE_CLANG_VERSIONS=9.0
    $ export CONAN_BUILD_TYPES=Debug

    $ python build.py


There are also two additional parameters of the ``add_common_builds``:

- **pure_c**: (Default True) If your project is C++, pass the **pure_c=False** to add both 
              combinations using **libstdc** and **libstdc++11** for the setting **compiler.libcxx**. 
              When True, the default profile value of ``libcxx`` will be applied.
              If you don't want ``libcxx`` value to apply 
              to your binary packages you have to use the ``configure`` method to remove it:
              
```
    def configure(self):
        del self.settings.compiler.libcxx
```

- **shared_option_name**: If your conanfile.py have an option to specify **shared**/**static** packages, you can add new build combinations for static/shared packages.
- **dll_with_static_runtime**: Will add also the combination of runtime MT with shared libraries.

```
from conan.packager import ConanMultiPackager

if __name__ == "__main__":
    builder = ConanMultiPackager()
    builder.add_common_builds(shared_option_name="mypackagename:shared", pure_c=False)
    builder.run()
```

## Filtering the configurations

You can use **builder.add_common_builds** method and remove then some configurations. EX: Remove the GCC 4.6 packages with build_type=Debug:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(username="myuser")
        builder.add_common_builds()
        filtered_builds = []
        for settings, options, env_vars, build_requires, reference in builder.items:
            if settings["compiler.version"] != "4.6" and settings["build_type"] != "Debug":
                 filtered_builds.append([settings, options, env_vars, build_requires])
        builder.builds = filtered_builds
        builder.run()


## Using Docker

Instance ConanMultiPackager with the parameter **use_docker=True**, or declare the environment variable **CONAN_USE_DOCKER**:
It will launch, when needed, a container for the current build configuration that is being built (only for Linux builds).

There are docker images available for different gcc versions: 4.6, 4.8, 4.9, 5, 6, 7 and clang versions: 3.8, 3.9, 4.0.

The containers will share the conan storage directory, so the packages will be generated in your conan directory.

**Example**:


    from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager()
	    builder.add_common_builds()
	    builder.run()

And run the build.py:

    $ export CONAN_USERNAME=myuser
    $ export CONAN_GCC_VERSIONS=4.9
    $ export CONAN_DOCKER_IMAGE=lasote/conangcc49
    $ export CONAN_USE_DOCKER=1
    $ python build.py


It will generate a set of build configurations (profiles) for gcc 4.9 and will run it inside a container of the ``lasote/conangcc49`` image.

If you want to run the arch="x86" build inside a docker container of 32 bits you can set the parameter ``docker_32_images`` in the 
ConanMultiPackager constructor or set the environment variable ``CONAN_DOCKER_32_IMAGES``. In this case, the docker image name to use
will be appended with ``-i386``. 

The Docker images used by default both for 64 and 32 bits are pushed to dockerhub and its Dockerfiles are  available in the 
[conan-docker-tools](https://github.com/conan-io/conan-docker-tools) repository.

### Running scripts and executing commands before to build on Docker

When Conan Package Tools uses Docker to build your packages, sometimes you need to execute a "before build" step. If
you need to install packages, change files or create a setup, there is an option for that: **docker_entry_script**

**Example**:

This example shows how to install *tzdata* package by apt-get, before to build the Conan package.

    from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
        command = "sudo apt-get -qq update && sudo apt-get -qq install -y tzdata"
	    builder = ConanMultiPackager(use_docker=True, docker_image='lasote/conangcc7', docker_entry_script=command)
	    builder.add_common_builds()
	    builder.run()

Also, it's possible to run some internal script, before to build the package:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        command = "python bootstrap.py"
        builder = ConanMultiPackager(use_docker=True, docker_image='lasote/conangcc7', docker_entry_script=command)
        builder.add_common_builds()
        builder.run()


## Specifying a different base profile

The options, settings and environment variables that the ``add_common_builds()`` method generate, are applied into the default profile
of the conan installation. If you want to use a different default profile you can pass the name of the profile in the ``run()`` method.


 **Example**:


    from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager()
	    builder.add_common_builds(clang_versions=["3.8", "3.9"])
	    builder.run("myclang")


# The CI integration

If you are going to use a CI server to generate different binary packages for your recipe, the best approach is to control
the build configurations with environment variables.

So, having a generic ``build.py`` should be enough for almost all the cases:


    from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager()
	    builder.add_common_builds(shared_option_name="mypackagename:shared", pure_c=False)
	    builder.run()

Then, in your CI configuration, you can declare different environment variables to limit the build configurations to an specific compiler version,
using a specific docker image etc.

For example, if you declare the following environment variables:

    CONAN_GCC_VERSIONS=4.9
    CONAN_DOCKER_IMAGE=lasote/conangcc49

the ``add_common_builds()`` method will only add different build configurations for GCC=4.9 and will run them in a docker container.

You can see working integrations with Travis and Appveyor in the zlib repository [here](https://github.com/lasote/conan-zlib)


## Travis integration

Travis CI can generate a build with multiple jobs defining a matrix with environment variables.
We can configure the builds to be executed in the jobs by defining some environment variables.

The following is a real example of a **.travis.yml** file that will generate packages for Linux gcc (4.9, 5, 6), Linux Clang (3.9 and 4.0) and OSx with apple-clang (8.0, 8.1 and 9.0).

Remember, you can use `conan new` command to generate the base files for appveyor, travis etc. Check `conan new --help`.


**.travis.yml** example:


    env:
       global:
         - CONAN_REFERENCE: "zlib/1.2.11" # ADJUST WITH YOUR REFERENCE!
         - CONAN_USERNAME: "conan" # ADJUST WITH YOUR REFERENCE USERNAME!
         - CONAN_LOGIN_USERNAME: "lasote" # ADJUST WITH YOUR LOGIN USERNAME!
         - CONAN_CHANNEL: "testing" # ADJUST WITH YOUR CHANNEL!
         - CONAN_UPLOAD: "https://api.bintray.com/conan/conan-community/conan" # ADJUST WITH YOUR REMOTE!
         - CONAN_STABLE_BRANCH_PATTERN: "release/*"
         - CONAN_UPLOAD_ONLY_WHEN_STABLE: 1 # Will only upload when the branch matches "release/*"

    linux: &linux
       os: linux
       sudo: required
       language: python
       python: "3.6"
       services:
         - docker
    osx: &osx
       os: osx
       language: generic
    matrix:
       include:

          - <<: *linux
            env: CONAN_GCC_VERSIONS=4.9 CONAN_DOCKER_IMAGE=lasote/conangcc49
          - <<: *linux
            env: CONAN_GCC_VERSIONS=5 CONAN_DOCKER_IMAGE=lasote/conangcc5
          - <<: *linux
            env: CONAN_GCC_VERSIONS=6 CONAN_DOCKER_IMAGE=lasote/conangcc6
          - <<: *linux
            env: CONAN_GCC_VERSIONS=7 CONAN_DOCKER_IMAGE=lasote/conangcc7
          - <<: *linux
            env: CONAN_CLANG_VERSIONS=3.9 CONAN_DOCKER_IMAGE=lasote/conanclang39
          - <<: *linux
            env: CONAN_CLANG_VERSIONS=4.0 CONAN_DOCKER_IMAGE=lasote/conanclang40
          - <<: *osx
            osx_image: xcode7.3
            env: CONAN_APPLE_CLANG_VERSIONS=7.3
          - <<: *osx
            osx_image: xcode8.2
            env: CONAN_APPLE_CLANG_VERSIONS=8.0
          - <<: *osx
            osx_image: xcode8.3
            env: CONAN_APPLE_CLANG_VERSIONS=8.1
          - <<: *osx
            osx_image: xcode9
            env: CONAN_APPLE_CLANG_VERSIONS=9.0

    install:
      - chmod +x .travis/install.sh
      - ./.travis/install.sh

    script:
      - chmod +x .travis/run.sh
      - ./.travis/run.sh

You can also use multiples "pages" to split the builds in different jobs (Check pagination section first to understand):

**.travis.yml**

    env:
       global:
         - CONAN_REFERENCE: "zlib/1.2.11" # ADJUST WITH YOUR REFERENCE!
         - CONAN_USERNAME: "conan" # ADJUST WITH YOUR REFERENCE USERNAME!
         - CONAN_LOGIN_USERNAME: "lasote" # ADJUST WITH YOUR LOGIN USERNAME!
         - CONAN_CHANNEL: "testing" # ADJUST WITH YOUR CHANNEL!
         - CONAN_UPLOAD: "https://api.bintray.com/conan/conan-community/conan" # ADJUST WITH YOUR REMOTE!
         - CONAN_STABLE_BRANCH_PATTERN: "release/*"
         - CONAN_UPLOAD_ONLY_WHEN_STABLE: 1 # Will only upload when the branch matches "release/*"

    linux: &linux
       os: linux
       sudo: required
       language: python
       python: "3.6"
       services:
         - docker
    osx: &osx
       os: osx
       language: generic
    matrix:
       include:

          - <<: *linux
            env: CONAN_GCC_VERSIONS=4.9 CONAN_DOCKER_IMAGE=lasote/conangcc49 CONAN_CURRENT_PAGE=1

          - <<: *linux
            env: CONAN_GCC_VERSIONS=4.9 CONAN_DOCKER_IMAGE=lasote/conangcc49 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_GCC_VERSIONS=5 CONAN_DOCKER_IMAGE=lasote/conangcc5 CONAN_CURRENT_PAGE=1

           - <<: *linux
            env: CONAN_GCC_VERSIONS=5 CONAN_DOCKER_IMAGE=lasote/conangcc5 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_GCC_VERSIONS=6 CONAN_DOCKER_IMAGE=lasote/conangcc6 CONAN_CURRENT_PAGE=1

          - <<: *linux
            env: CONAN_GCC_VERSIONS=6 CONAN_DOCKER_IMAGE=lasote/conangcc6 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_CLANG_VERSIONS=3.9 CONAN_DOCKER_IMAGE=lasote/conanclang39 CONAN_CURRENT_PAGE=1

           - <<: *linux
            env: CONAN_CLANG_VERSIONS=3.9 CONAN_DOCKER_IMAGE=lasote/conanclang39 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_CLANG_VERSIONS=4.0 CONAN_DOCKER_IMAGE=lasote/conanclang40 CONAN_CURRENT_PAGE=1

          - <<: *linux
            env: CONAN_CLANG_VERSIONS=4.0 CONAN_DOCKER_IMAGE=lasote/conanclang40 CONAN_CURRENT_PAGE=2

          - <<: *osx
            osx_image: xcode7.3
            env: CONAN_APPLE_CLANG_VERSIONS=7.3 CONAN_CURRENT_PAGE=1

          - <<: *osx
            osx_image: xcode7.3
            env: CONAN_APPLE_CLANG_VERSIONS=7.3 CONAN_CURRENT_PAGE=2

          - <<: *osx
            osx_image: xcode8.2
            env: CONAN_APPLE_CLANG_VERSIONS=8.0 CONAN_CURRENT_PAGE=1

          - <<: *osx
            osx_image: xcode8.2
            env: CONAN_APPLE_CLANG_VERSIONS=8.0 CONAN_CURRENT_PAGE=2

          - <<: *osx
            osx_image: xcode8.3
            env: CONAN_APPLE_CLANG_VERSIONS=8.1 CONAN_CURRENT_PAGE=1

          - <<: *osx
            osx_image: xcode8.3
            env: CONAN_APPLE_CLANG_VERSIONS=8.1 CONAN_CURRENT_PAGE=2

    install:
      - chmod +x .travis/install.sh
      - ./.travis/install.sh

    script:
      - chmod +x .travis/run.sh
      - ./.travis/run.sh

**.travis/install.sh**

    #!/bin/bash

    set -e
    set -x

    if [[ "$(uname -s)" == 'Darwin' ]]; then
        brew update || brew update
        brew outdated pyenv || brew upgrade pyenv
        brew install pyenv-virtualenv
        brew install cmake || true

        if which pyenv > /dev/null; then
            eval "$(pyenv init -)"
        fi

        pyenv install 2.7.10
        pyenv virtualenv 2.7.10 conan
        pyenv rehash
        pyenv activate conan
    fi

    pip install conan --upgrade
    pip install conan_package_tools==0.3.7dev12

    conan user


If you want to "pin" a **conan_package_tools** version use:

    pip install conan_package_tools==0.3.2

That version will be used also in the docker images.


**.travis/run.sh**


    #!/bin/bash

    set -e
    set -x

    if [[ "$(uname -s)" == 'Darwin' ]]; then
        if which pyenv > /dev/null; then
            eval "$(pyenv init -)"
        fi
        pyenv activate conan
    fi

    python build.py


Remember to set the CONAN_PASSWORD variable in the travis build control panel!


## Appveyor integration

This is very similar to Travis CI. With the same **build.py** script we have the following **appveyor.yml** file:

    build: false

    environment:
        PYTHON: "C:\\Python27"
        PYTHON_VERSION: "2.7.8"
        PYTHON_ARCH: "32"

        CONAN_REFERENCE: "lib/1.0"
        CONAN_USERNAME: "lasote"
        CONAN_LOGIN_USERNAME: "lasote"
        CONAN_CHANNEL: "stable"
        VS150COMNTOOLS: "C:\\Program Files (x86)\\Microsoft Visual Studio\\2017\\Community\\Common7\\Tools\\"
        CONAN_UPLOAD: "https://api.bintray.com/conan/luisconanorg/fakeconancenter"
        CONAN_REMOTES: "https://api.bintray.com/conan/luisconanorg/conan-testing"

        matrix:
            - APPVEYOR_BUILD_WORKER_IMAGE: Visual Studio 2015
              CONAN_VISUAL_VERSIONS: 12
            - APPVEYOR_BUILD_WORKER_IMAGE: Visual Studio 2015
              CONAN_VISUAL_VERSIONS: 14
            - APPVEYOR_BUILD_WORKER_IMAGE: Visual Studio 2017
              CONAN_VISUAL_VERSIONS: 15


    install:
      - set PATH=%PATH%;%PYTHON%/Scripts/
      - pip.exe install conan_package_tools --upgrade
      - conan user # It creates the conan data directory

    test_script:
      - python build.py


- Remember to set the **CONAN_PASSWORD** variable in appveyor build control panel!

## Bamboo CI integration

[Bamboo](https://www.atlassian.com/software/bamboo) is a commercial CI tool developed by Atlassian.
When building from bamboo, several environment variables get set during builds.

If the env var **bamboo_buildNumber** is set and the branch name (**bamboo_planRepository_branch** env var) matches **stable_branch_pattern**, then the channel name gets set to ```stable```.

## Jenkins CI integration

[Jenkins](https://jenkins.io/) is an open source CI tool that was originally forked from hudson.
When building on jenkins, several environment variables get set during builds.

If the env var **JENKINS_URL** is set and the branch name (**BRANCH_NAME** env var) matches **stable_branch_pattern**, then the channel name gets set to ```stable```.

Currently, only the pipeline builds set the **BRANCH_NAME** env var automatically.

## GitLab CI integration

[GitLab CI](https://about.gitlab.com/features/gitlab-ci-cd/) is a commercial CI tool developed by GitLab.
When building on gitlab-ci, several environment variables get set during builds.

If the env var **GITLAB_CI** is set and the branch name (**CI_BUILD_REF_NAME** env var) matches **stable_branch_pattern**, then the channel name gets set to ```stable```.


## Upload packages

You can upload the generated packages automatically to a conan-server using the following environment variables (parameters also available):

- Remote url:

        CONAN_UPLOAD: "https://api.bintray.com/conan/conan-community/conan"

- User to login in the remote:

        CONAN_LOGIN_USERNAME: "lasote"

- User (to generate the packages in that user namespace, e.j: zlib/1.2.11@conan/stable):


        CONAN_USERNAME: "conan"

- Channel (to generate the packages in that channel namespace, e.j: zlib/1.2.11@conan/testing):

        CONAN_CHANNEL: "testing"

- If the detected branch in the CI matches the pattern, declare the CONAN_CHANNEL as stable:

        CONAN_STABLE_BRANCH_PATTERN: "release/*"



## Pagination

Sometimes, if your library is big or complex enough in terms of compilation time, the CI server could reach the maximum time of execution,
because it's building, for example, 20 different binary packages for your library in the same machine.

You can split the different build configurations in different "pages". So, you can configure your CI to run more "worker" machines, one per "page".

There are two approaches:

### Sequencial distribution

By simply passing two pagination parameters, **curpage** and **total_pages** or the corresponding environment variables:

    $ export CONAN_TOTAL_PAGES=3
    $ export CONAN_CURRENT_PAGE=1

    $ python build.py


If you added 10 different build configurations to the builder:

- With **CONAN_CURRENT_PAGE=1** it runs only 1,4,7,10
- With **CONAN_CURRENT_PAGE=2** it runs only 2,5,8
- With **CONAN_CURRENT_PAGE=3** it runs only 3,6,9

In your CI server you can configure a matrix with different "virtual machines" or "jobs" or "workers":
In each "machine" you can specify a different CONAN_CURRENT_PAGE environment variable.
So your different configurations will be distributed in the different machines.


### Named pages

By adding builds to the **named_builds** dictionary, and passing **curpage** with the page name:

    from conan.packager import ConanMultiPackager
    from collections import defaultdict

    if __name__ == '__main__':
        builder = ConanMultiPackager(curpage="x86", total_pages=2)
        named_builds = defaultdict(list)
        builder.add_common_builds(shared_option_name="bzip2:shared", pure_c=True)
        for settings, options, env_vars, build_requires, reference in builder.items:
            named_builds[settings['arch']].append([settings, options, env_vars, build_requires, reference])
        builder.named_builds = named_builds
        builder.run()

named_builds not have a dictionary entry for x86 and another for x86_64:

- for **CONAN_CURRENT_PAGE="x86"** it would do all x86 builds
- for **CONAN_CURRENT_PAGE="x86_64"** it would do all x86_64 builds



### Generating multiple references for the same recipe

You can add a different reference in the builds tuple, so for example, if your recipe has no "version"
field, you could generate several versions in the same build script. Conan package tools will export
the recipe using the different reference automatically:

    from conan.packager import ConanMultiPackager

    if __name__ == '__main__':
        builder = ConanMultiPackager()
        builder.add_common_builds(reference="mylib/1.0@conan/stable")
        builder.add_common_builds(reference="mylib/2.0@conan/stable")
        builder.run()


<a name="bintray"></a>
## Working with Bintray: Configuring repositories

Use the argument `upload` or environment variable `CONAN_UPLOAD` to set the URL of the repository where you want to
upload your packages. Will be also used to read from it.

Use `CONAN_PASSWORD` environment variable to set the API key from Bintray. If your username in Bintray doesn't match with
the specified `CONAN_USERNAME` specify the variable `CONAN_LOGIN_USERNAME` or the parameter `login_username` to ConanMultiPackager .

If you are using travis or appveyor you can use a hidden enviroment variable from the repository setup
package.

To get an API key in Bintray to "Edit profile"/"API key".

Use the argument `remotes` or environment variable `CONAN_REMOTES` to configure additional repositories containing
needed requirements.

**Example:** Add your personal Bintray repository to retrieve and upload your packages and also some other different
repositories to read some requirements.

In your `.travis.yml` or `appveyor.yml` files declare the environment variables:

    CONAN_UPLOAD="https://api.bintray.com/mybintrayuser/conan_repository"
    CONAN_REMOTES="https://api.bintray.com/other_bintray_user/conan-repo, https://api.bintray.com/other_bintray_user2/conan-repo"

Or in your `build.py`:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(username="myuser",
                                     upload="https://api.bintray.com/mybintrayuser/conan_repository",
                                     remotes="https://api.bintray.com/other_bintray_user/conan-repo, https://api.bintray.com/other_bintray_user2/conan-repo")
        builder.add_common_builds()
        builder.run()



## Visual Studio auto-configuration

When the builder detects a Visual Studio compiler and its version, it will automatically configure the execution environment
for the "conan test" command with the **vcvarsall.bat** script (provided by all Microsoft Visual Studio versions).
So you can compile your project with the right compiler automatically, even without CMake.

## MinGW builds

MinGW compiler builds are also supported. You can use this feature with Appveyor.

You can choose different MinGW compiler configurations:

- **Version**: 4.8 and 4.9 are supported
- **Architecture**: x86 and x86_64 are supported
- **Exceptions**: seh and sjlj are supported
- **Threads**: posix and win32 are supported


Using **MINGW_CONFIGURATIONS** env variable in Appveyor:

    MINGW_CONFIGURATIONS: '4.9@x86_64@seh@posix, 4.9@x86_64@seh@win32'

Check an example [here](https://github.com/lasote/conan-zlib/blob/release/1.2.8/appveyor.yml)


## Clang builds

Clang compiler builds are also supported. You can use this feature with TravisCI.

You can choose different Clang compiler configurations:

- **Version**: 3.8, 3.9 and 4.0 are supported
- **Architecture**: x86 and x86_64 are supported

Using **CONAN_CLANG_VERSIONS** env variable in Travis ci or Appveyor:

    CONAN_CLANG_VERSIONS = "3.8,3.9,4.0"


# FULL REFERENCE

## ConanMultiPackager parameters reference

- **args**: List with the parameters that will be passed to "conan test" command. e.j: args=['--build', 'all']. Default sys.argv[1:]
- **username**: Your conan username
- **gcc_versions**: List with a subset of gcc_versions. Default ["4.9", "5", "6", "7"]
- **clang_versions**: List with a subset of clang_versions. Default ["3.8", "3.9", "4.0"]
- **apple_clang_versions**: List with a subset of apple-clang versions. Default ["6.1", "7.3", "8.0"]
- **visual_versions**: List with a subset of Visual Studio versions. Default [10, 12, 14]
- **visual_runtimes**: List containing Visual Studio runtimes to use in builds. Default ["MT", "MD", "MTd", "MDd"]
- **mingw_configurations**: Configurations for MinGW
- **archs**: List containing specific architectures to build for. Default ["x86", "x86_64"]
- **use_docker**: Use docker for package creation in Linux systems.
- **docker_image_skip_update**: If defined, it will skip the initialization update of "conan package tools" and "conan" in the docker image. By default is False.
- **docker_entry_script**: Command to be executed before to build when running Docker.
- **docker_32_images**: If defined, and the current build is arch="x86" the docker image name will be appended with "-i386". e.j: "lasote/conangcc63-i386"
- **curpage**: Current page of packages to create
- **total_pages**: Total number of pages
- **vs10_x86_64_enabled**: Flag indicating whether or not to build for VS10 64bits. Default [False]
- **upload_retry**: Num retries in upload in case of failure.
- **remotes**: List of URLs separated by "," for the additional remotes (read).
- **upload**: URL of the repository where we want to use to upload the packages.
- **upload_only_when_stable**: Will try to upload only if the channel is the stable channel
- **build_types**: List containing specific build types. Default ["Release", "Debug"]
- **skip_check_credentials**: Conan will check the user credentials before building the packages. Default [False]
- **allow_gcc_minors** Declare this variable if you want to allow gcc >=5 versions with the minor (5.1, 6.3 etc).
- **exclude_vcvars_precommand** For Visual Studio builds, it exclude the vcvars call to set the environment.

Upload related parameters:

- **upload**: True or False. Default False
- **reference**: Reference of the package to upload. Ex: "zlib/1.2.8"
- **password**. Conan Password
- **remote**: Alternative remote name. Default "default"
- **stable_branch_pattern**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *stable* channel. Default "master"
- **stable_channel**: Stable channel, default "stable".
- **channel**: Channel where your packages will be uploaded if previous parameter doesn't match


## Complete ConanMultiPackager methods reference:

- **add_common_builds(shared_option_name=None, pure_c=True, dll_with_static_runtime=False)**: Generate a set of package configurations and add them to the
  list of packages that will be created.

    - **shared_option_name**: If given, ConanMultiPackager will add different configurations for -o shared=True and -o shared=False.
    - **pure_c**: ConanMultiPackager won't generate different builds for the **libstdc++** c++ standard library, because it is a pure C library.
    - **dll_with_static_runtime**: generate also build for "MT" runtime when the library is shared.

- **login(remote_name, user=None, password=None, force=False)**: Performs a `conan user` command in the specified remote. If `force` the login will be called
 every time, otherwise, for the same remote, ConanMultiPackager will call `conan user` only once even with multiple calls to the login() method.

- **add(settings=None, options=None, env_vars=None, build_requires=None)**: Add a new build configuration, so a new binary package will be built for the specified configuration.

- **run()**: Run the builds (Will invoke conan create for every specified configuration)

- **upload_packages()**: Called automatically by "run()" when upload is enabled. Can be called explicitly.


## Environment configuration

You can also use environment variables to change the behavior of ConanMultiPackager, so that you don't pass parameters to the ConanMultiPackager constructor.

This is especially useful for CI integration.

- **CONAN_USERNAME**: Your conan username
- **CONAN_REFERENCE**: Reference of the package to upload, e.g. "zlib/1.2.8"
- **CONAN_PASSWORD**: Conan Password, or API key if you are using Bintray.
- **CONAN_REMOTES**: List of URLs separated by "," for the additional remotes (read).
- **CONAN_UPLOAD**: URL of the repository where we want to use to upload the packages.
- **CONAN_UPLOAD_RETRY**: If defined, in case of fail retries to upload again the specified times
- **CONAN_UPLOAD_ONLY_WHEN_STABLE**: If defined, will try to upload the packages only when the current channel is the stable one.
- **CONAN_SKIP_CHECK_CREDENTIALS**: Force to check user credentials before to build when upload is required. By default is False.
- **CONAN_DOCKER_ENTRY_SCRIPT**: Command to be executed before to build when running Docker.
- **CONAN_GCC_VERSIONS**: Gcc versions, comma separated, e.g. "4.6,4.8,5,6"
- **CONAN_CLANG_VERSIONS**: Clang versions, comma separated, e.g. "3.8,3.9,4.0"
- **CONAN_APPLE_CLANG_VERSIONS**: Apple clang versions, comma separated, e.g. "6.1,8.0"
- **CONAN_ARCHS**: Architectures to build for, comma separated, e.g. "x86,x86_64"
- **CONAN_BUILD_TYPES**: Build types to build for, comma separated, e.g. "Release,Debug"
- **CONAN_VISUAL_VERSIONS**: Visual versions, comma separated, e.g. "12,14"
- **CONAN_VISUAL_RUNTIMES**: Visual runtimes, comma separated, e.g. "MT,MD"
- **CONAN_USE_DOCKER**: If defined will use docker
- **CONAN_CURRENT_PAGE**:  Current page of packages to create
- **CONAN_TOTAL_PAGES**: Total number of pages
- **CONAN_DOCKER_IMAGE**: If defined and docker is being used, it will use this dockerimage instead of the default images, e.g. "lasote/conangcc63"
- **CONAN_DOCKER_IMAGE_SKIP_UPDATE**: If defined, it will skip the initialization update of "conan package tools" and "conan" in the docker image. By default is False.
- **CONAN_DOCKER_32_IMAGES**: If defined, and the current build is arch="x86" the docker image name will be appended with "-i386". e.j: "lasote/conangcc63-i386"
- **CONAN_STABLE_BRANCH_PATTERN**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *CONAN_STABLE_CHANNEL* channel. Default "master". E.j: "release/*"
- **CONAN_STABLE_CHANNEL**: Stable channel name, default "stable"
- **CONAN_STABLE_USERNAME**: Your conan username in case the `CONAN_STABLE_BRANCH_PATTERN` matches. Optional. If not defined `CONAN_USERNAME` is used.
- **CONAN_STABLE_PASSWORD**: Password for `CONAN_STABLE_USERNAME`. Default: `CONAN_PASSWORD`
- **CONAN_CHANNEL**: Channel where your packages will be uploaded if the previous parameter doesn't match
- **CONAN_PIP_PACKAGE**: Specify a conan package to install (by default, installs the latest) e.j conan==0.0.1rc7
- **MINGW_CONFIGURATIONS**: Specify a list of MinGW builds. See MinGW builds section.
- **CONAN_BASH_PATH**: Path to a bash executable. Used only in windows to help the tools.run_in_windows_bash() function to locate our Cygwin/MSYS2 bash.
  Set it with the bash executable path if it’s not in the PATH or you want to use a different one.
- **CONAN_DOCKER_USE_SUDO** Force to use "sudo" when invoking conan. By default, only with Windows. "False" to deactivate.
- **CONAN_ALLOW_GCC_MINORS** Declare this variable if you want to allow gcc >=5 versions with the minor (5.1, 6.3 etc).
- **CONAN_EXCLUDE_VCVARS_PRECOMMAND** For Visual Studio builds, it exclude the vcvars call to set the environment.
- **CONAN_BUILD_REQUIRES** You can specify additional build requires for the generated profile with an environment variable following the same profile syntax and separated by ","
  i.e ``CONAN_BUILD_REQUIRES: mingw-installer/7.1@conan/stable, pattern: other/1.0@conan/stable`` 

# Full example

You can see the full zlib example [here](https://github.com/lasote/conan-zlib)
