# Conan Package Tools [![Build Status](https://travis-ci.org/conan-io/conan-package-tools.svg?branch=master)](https://travis-ci.org/conan-io/conan-package-tools)

This package simplifies the generation of multiple packages when using the [conan package manager](http://conan.io).

It also eases the integration with  [TravisCI](https://travis-ci.org/) and [Appveyor](http://www.appveyor.com/), and allows for the automation of package creation in CI servers, as well as the upload of the generated packages to [conan](http://conan.io).

## Features:

- Easy definition of packages that will be created.
- Pagination of package creation - you can split the build in different tasks (ideal for CI).
- You can automatically use Docker for auto-generating packages for gcc 4.6, 4.8, 4.9, 5.2, 5.3, 5.4, 6.3 and clang 3.8, 3.9, 4.0, in a clean environment, every time.
- For Windows Visual Studio builds, auto-detect the Visual Studio version and prepare the environment to point to that compiler.
- Upload packages directly to conan.io (or your own custom conan server)
- Great and easy integration with [TravisCI](https://travis-ci.org/) and [Appveyor](http://www.appveyor.com/)


## Installation

    $ pip install conan_package_tools


Or you can [clone this repository](http://github.com/conan-io/conan-package-tools) and store its location in PYTHONPATH.


## Quick start

You must have a **conanfile.py** file and a **test_package** folder in your current directory and the **conan test_package** command must work.
If you don't have it ready, take a look to [Getting started creating packages](http://docs.conan.io/en/latest/packaging/getting_started.html)

Now create a **build.py** file in the root of your project and instance a **ConanMultiPackager**:


    from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager(username="myuser")
	    builder.add_common_builds()
	    builder.run()

Generate the packages:

	$> python build.py


If your project is C++, pass the **pure\_c=False** parameter to **add_common_builds**,  and will be generated packages with the setting *compiler.libcxx*.

If your conanfile.py have an option to specify **shared**/**static** packages you can also pass it to **add_common_builds** and it will generate the package configurations corresponding to shared and static packages:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager()
        builder.add_common_builds(shared_option_name="bzip2:shared", pure_c=True)
        builder.run()

If you are using Visual Studio and you want build shared libraries with static runtime (MT, MTd) you can pass **dll_with_static_runtime** parameter to True in **add_common_builds**.


## Working with Bintray: Configuring repositories

Use the argument `upload` or environment variable `CONAN_UPLOAD` to set the URL of the repository where you want to
upload your packages. Will be also used to read from it.

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


## Select the packages to be generated

You can use **builder.add\_common\_builds** method and remove some configurations. EX: just keep the compiler 4.6 packages:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(username="myuser")
        builder.add_common_builds()
        filtered_builds = []
        for settings, options, env_vars, build_requires in builder.builds:
            if settings["compiler.version"] == "4.6":
                 filtered_builds.append([settings, options, env_vars, build_requires])
        builder.builds = filtered_builds
        builder.run()


Or add package's configurations without these method (settings, options, environment variables and build requires):

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


Using **MINGW_CONFIGURATIONS** env variable:

    os.environ["MINGW_CONFIGURATIONS"] = '4.9@x86_64@seh@posix, 4.9@x86_64@seh@win32'


Or passing a list to ConanMultiPackager constructor:

    mingw_configurations = [("4.9", "x86_64", "seh", "posix"),
                            ("4.9", "x86_64", "sjlj", "posix"),
                            ("4.9", "x86", "sjlj", "posix"),
                            ("4.9", "x86", "dwarf2", "posix")]
    builder = ConanMultiPackager(username="lasote", mingw_configurations=mingw_configurations)
    builder.add_common_builds(pure_c=False)
    builder.run()

## Clang builds

Clang compiler builds are also supported. You can use this feature with TravisCI.

You can choose different Clang compiler configurations:

- **Version**: 3.8, 3.9 and 4.0 are supported
- **Architecture**: x86 and x86_64 are supported

Using **CONAN_CLANG_VERSIONS** env variable:

    os.environ["CONAN_CLANG_VERSIONS"] = "3.8,3.9,4.0"

## Pagination

You can split builds in pages, this is very useful with CI servers like Travis to obey job time limit or just segment specific build configurations.

There are two ways of setting pagination.

**Named pages**

By adding builds to the **named_builds** dictionary, and passing **curpage** with the page name:

    from conan.packager import ConanMultiPackager
    from collections import defaultdict

    if __name__ == '__main__':
        builder = ConanMultiPackager(curpage="x86", total_pages=2)
        named_builds = defaultdict(list)
        builder.add_common_builds(shared_option_name="bzip2:shared", pure_c=True)
        for settings, options, env_vars, build_requires in builder.builds:
            named_builds[settings['arch']].append([settings, options, env_vars, build_requires])
        builder.named_builds = named_builds
        builder.run()

named_builds not have a dictionary entry for x86 and another for x86_64:

- for **curpage="x86"** it would do all x86 builds
- for **curpage="x86_64"** it would do all x86_64 builds


**Sequencial distribution**

By simply passing two pagination parameters, **curpage** and **total_pages**:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(curpage=1, total_pages=3)
        builder.add_common_builds(shared_option_name="bzip2:shared", pure_c=True)
        builder.run()

If you added 10 package's to the builder:

- for **curpage=1** it would do builds 1,4,7,10
- for **curpage=2** it would do builds 2,5,8
- for **curpage=3** it would do builds 3,6,9

## Docker pack

If you instance ConanMultiPackager with the parameter **use_docker=True**,
it will launch N containers with a virtualized versions of Ubuntu.

We have different images available at **dockerhub**, for gcc versions 4.6, 4.8, 4.9, 5.2, 5.3, 6.2, 6.3 and for clang versions 3.8, 3.9, 4.0.

The containers will share the conan storage directory, so the packages will be generated in your conan directory.

You can also specify a subset of **gcc versions** with the parameter **gcc_versions** and the pagination is also available with the parameters **curpage** and **total_pages**.

You can also specify a subset of **clang versions** with the parameter **clang_versions** and the pagination is also available with the parameters **curpage** and **total_pages**.

## Upload packages

Instance ConanMultiPackager with the **upload** parameter and it will automatically upload the generated packages to a remote.

You also need to pass the parameters **reference** (ex: "bzip2/1.0.2"), **password** and **username**.

You can specify another remote name with parameter **remote**.

## Complete ConanMultiPackager parameters reference

- **args**: List with the parameters that will be passed to "conan test" command. e.j: args=['--build', 'all']. Default sys.argv[1:]
- **username**: Your conan username
- **gcc_versions**: List with a subset of gcc_versions. Default ["4.6", "4.8", "4.9", "5.2", "5.3", "5.4", "6.2", "6.3"]
- **clang_versions**: List with a subset of clang_versions. Default ["3.8", "3.9", "4.0"]
- **apple_clang_versions**: List with a subset of apple-clang versions. Default ["6.1", "7.3", "8.0"]
- **visual_versions**: List with a subset of Visual Studio versions. Default [10, 12, 14]
- **visual_runtimes**: List containing Visual Studio runtimes to use in builds. Default ["MT", "MD", "MTd", "MDd"]
- **mingw_configurations**: Configurations for MinGW
- **archs**: List containing specific architectures to build for. Default ["x86", "x86_64"]
- **use_docker**: Use docker for package creation in Linux systems.
- **curpage**: Current page of packages to create
- **total_pages**: Total number of pages
- **vs10_x86_64_enabled**: Flag indicating whether or not to build for VS10 64bits. Default [False]
- **upload_retry**: Num retries in upload in case of failure.
- **remotes**: List of URLs separated by "," for the additional remotes (read).
- **upload**: URL of the repository where we want to use to upload the packages.

Upload related parameters:

- **upload**: True or False. Default False
- **reference**: Reference of the package to upload. Ex: "zlib/1.2.8"
- **password**. Conan Password
- **remote**: Alternative remote name. Default "default"
- **stable_branch_pattern**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *stable* channel. Default "master"
- **stable_channel**: Stable channel, default "stable".
- **channel**: Channel where your packages will be uploaded if previous parameter doesn't match


## Environment configuration

You can also use environment variables to change the behavior of ConanMultiPackager, so that you don't pass parameters to the ConanMultiPackager constructor.

This is especially useful for CI integration.

- **CONAN_USERNAME**: Your conan username
- **CONAN_REFERENCE**: Reference of the package to upload, e.g. "zlib/1.2.8"
- **CONAN_PASSWORD**: Conan Password
- **CONAN_REMOTES**: List of URLs separated by "," for the additional remotes (read).
- **CONAN_UPLOAD**: URL of the repository where we want to use to upload the packages.
- **CONAN_UPLOAD_RETRY**: If defined, in case of fail retries to upload again the specified times
- **CONAN_GCC_VERSIONS**: Gcc versions, comma separated, e.g. "4.6,4.8,5.2,6.3"
- **CONAN_CLANG_VERSIONS**: Clang versions, comma separated, e.g. "3.8,3.9,4.0"
- **CONAN_APPLE_CLANG_VERSIONS**: Apple clang versions, comma separated, e.g. "6.1,8.0"
- **CONAN_ARCHS**: Architectures to build for, comma separated, e.g. "x86,x86_64"
- **CONAN_VISUAL_VERSIONS**: Visual versions, comma separated, e.g. "12,14"
- **CONAN_VISUAL_RUNTIMES**: Visual runtimes, comma separated, e.g. "MT,MD"
- **CONAN_USE_DOCKER**: If defined will use docker
- **CONAN_CURRENT_PAGE**:  Current page of packages to create
- **CONAN_TOTAL_PAGES**: Total number of pages
- **CONAN_DOCKER_IMAGE**: If defined and docker is being used, it will use this dockerimage instead of the default images, e.g. "lasote/conangcc63"
- **CONAN_STABLE_BRANCH_PATTERN**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *CONAN_STABLE_CHANNEL* channel. Default "master". E.j: "release/*"
- **CONAN_STABLE_CHANNEL**: Stable channel name, default "stable"
- **CONAN_STABLE_USERNAME**: Your conan username in case the `CONAN_STABLE_BRANCH_PATTERN` matches. Optional. If not defined `CONAN_USERNAME` is used.
- **CONAN_STABLE_PASSWORD**: Password for `CONAN_STABLE_USERNAME`. Default: `CONAN_PASSWORD`
- **CONAN_CHANNEL**: Channel where your packages will be uploaded if the previous parameter doesn't match
- **CONAN_PIP_PACKAGE**: Specify a conan package to install (by default, installs the latest) e.j conan==0.0.1rc7
- **MINGW_CONFIGURATIONS**: Specify a list of MinGW builds. See MinGW builds section.


## Travis integration

Travis CI can generate a build with multiple jobs defining a matrix with environment variables.
We can configure the builds to be executed in the jobs by defining some environment variables.

The following is a real example of a *.travis.yml* file that will generate packages for **Linux (gcc 4.6-5.2) and OSx for xcode6.4 and xcode7.3 and xcode8.2**
It uses 2 different jobs for each compiler version.

Remember, from conan 0.24 you can use `conan new` command to generate the base files for appveyor, travis etc. Check `conan new --help`.

.travis.yml example:

**.travis.yml**


   env:
       global:
         - CONAN_REFERENCE: "lib/1.0"
         - CONAN_USERNAME: "lasote"
         - CONAN_CHANNEL: "stable"
         - CONAN_UPLOAD: "https://api.bintray.com/mybintrayuser/myconanrepo"
         - CONAN_REMOTES: "https://api.bintray.com/otherbintrayuser/otherconanrepo"

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
            env: CONAN_GCC_VERSIONS=5.4 CONAN_DOCKER_IMAGE=lasote/conangcc54

          - <<: *linux
            env: CONAN_GCC_VERSIONS=6.3 CONAN_DOCKER_IMAGE=lasote/conangcc63

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

    install:
      - chmod +x .travis/install.sh
      - ./.travis/install.sh

    script:
      - chmod +x .travis/run.sh
      - ./.travis/run.sh


You can also use multiples "pages" to split the builds in different jobs:

**.travis.yml**

    env:
       global:
         - CONAN_REFERENCE: "lib/1.0"
         - CONAN_USERNAME: "lasote"
         - CONAN_CHANNEL: "stable"
         - CONAN_UPLOAD: "https://api.bintray.com/mybintrayuser/myconanrepo"
         - CONAN_REMOTES: "https://api.bintray.com/otherbintrayuser/otherconanrepo"
         - CONAN_TOTAL_PAGES: 2

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
            env: CONAN_GCC_VERSIONS=5.4 CONAN_DOCKER_IMAGE=lasote/conangcc54 CONAN_CURRENT_PAGE=1

           - <<: *linux
            env: CONAN_GCC_VERSIONS=5.4 CONAN_DOCKER_IMAGE=lasote/conangcc54 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_GCC_VERSIONS=6.3 CONAN_DOCKER_IMAGE=lasote/conangcc63 CONAN_CURRENT_PAGE=1

          - <<: *linux
            env: CONAN_GCC_VERSIONS=6.3 CONAN_DOCKER_IMAGE=lasote/conangcc63 CONAN_CURRENT_PAGE=2

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
      - pip.exe install conan --upgrade
      - pip.exe install conan_package_tools==0.3.7dev12
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

# Full example

You can see the full zlib example [here](https://github.com/lasote/conan-zlib)
