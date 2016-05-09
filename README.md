# Conan Package Tools

This package makes easy the generation of multiple packages using [conan package manager](http://conan.io).

Also ease the integration with  [TravisCI](https://travis-ci.org/) and [Appveyor](http://www.appveyor.com/) and allows to automate the package creation in CI servers and the upload to [conan](http://conan.io).

## Features:

- Easy definition of packages that will be created.
- Paginate the packages creation, you can split the build in some different tasks (ideal for CI).
- You can use automatically Docker for auto generate packages for gcc 4.6, 4.8, 4.9, 5.2, 5.3 in a clean environment every time.
- For Windows Visual Studio builds, auto detect visual version and prepare the environment to point to that compiler.
- Upload packages directly to conan.io (or your custom conan server)
- Great and easy integration with [TravisCI](https://travis-ci.org/) and [Appveyor](http://www.appveyor.com/)


## Install

    $ pip install conan_package_tools


Or you can [clone this repository](http://github.com/conan-io/conan-package-tools) and store its location to PYTHONPATH.


## Quick start

First is assumes that you are creating a conan's package.
You must have a **conanfile.py** file and a **test** folder in your current directory and **conan test** command must work.
If you don't have it ready, take a look to [Automatically creating and testing packages](http://docs.conan.io/en/latest/packaging/testing.html)

In your **test/conanfile.py** you need to make a small adjustement, the require (current library) needs to be configurable with environment variables:


    channel = os.getenv("CONAN_CHANNEL", "testing")
    username = os.getenv("CONAN_USERNAME", "myuser")

    class DefaultNameConan(ConanFile):
        ...
        requires = "zlib/1.2.8@%s/%s" % (username, channel)
        ...


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


## Select the packages to be generated

You can use **builder.add\_common\_builds** method and remove some configurations. EX: just keep the compiler 4.6 packages:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(username="myuser")
        builder.add_common_builds()
        filtered_builds = []
        for settings, options in builder.builds:
            if settings["compiler.version"] == "4.6":
                 filtered_builds.append([settings, options])
        builder.builds = filtered_builds
        builder.run()


Or add package's configurations without these method (settings and options):

	from conan.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager(username="myuser")
	    builder.add({"arch": "x86", "build_type": "Release"}, {"mypackage:option1": "ON"})
        builder.add({"arch": "x86_64", "build_type": "Release"}, {"mypackage:option1": "ON"})
        builder.add({"arch": "x86", "build_type": "Debug"}, {"mypackage:option2": "OFF", "mypackage:shared": True})
	    builder.run()


## Visual Studio auto-configuration

When the builder detects a "Visual Studio" compiler and it's version, it will automatically configure the execution environment for the "conan test" command with the **vcvarsall.bat** script (provided by all Microsoft Visual Studio versions).
So you can compile your project with the right compiler automatically, even without CMake.

## Pagination

You can launch partial builds passing two pagination parameters, **curpage** and **total_pages**.
It's very useful with CI servers like Travis, because you can split the builds in pages just passing some parameters:

    from conan.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(curpage=1, total_pages=2)
        builder.add_common_builds(shared_option_name="bzip2:shared", pure_c=True)
        builder.run()

If you added 10 package's to the builder, each page will execute 1 package generation, so in the example above will create the first 5 packages.


## Docker pack

If you instance ConanMultiPackager with the parameter **use_docker=True**,
it will launch N containers with a virtualized versions of Ubuntu.

We have available different images at **dockerhub**, for gcc versions 4.6, 4.8, 4.9, 5.2 and 5.3.

The containers will share the conan storage directory, so the packages will be generated in your conan's directory.

You can also specify a subset of **gcc versions** with the parameter **gcc_versions** and the pagination is also available with the parameters **curpage** and **total_pages**.

## Upload packages

Instance ConanMultiPackager with the **upload** parameter and it will automatically upload the generated packages to a remote.

You need also to pass the parameters **reference** (ex: "bzip2/1.0.2"), **password** and **username**.

You specify another remote name with parameter **remote**.

## Complete ConanMultiPackager parameters reference

- **args**: List with the parameters that will be passed to "conan test" command. e.j: args=['--build', 'all']. Default sys.argv[1:]
- **username**: Your conan's username
- **gcc_versions**: List with a subset of gcc_versions. Default ["4.6", "4.8", "4.9", "5.2", "5.3"]
- **apple_clang_versions**: List with a subset of apple-clang versions. Default ["5.0", "5.1", "6.0", "6.1", "7.0"]
- **visual_versions**: List with a subset of visual studio versions. Default [10, 12, 14]
- **visual_runtimes**: List containing visual studio runtimes to use in builds. Default ["MT", "MD", "MTd", "MDd"]
- **archs**: List containing specific architectures to build for. Default ["x86", "x86_64"]
- **use_docker**: Use docker for package creation in Linux systems.
- **curpage**: Current page of packages to create
- **total_pages**: Total of pages
- **vs10_x86_64_enabled**: Flag to tell that wether to build for VS10 64bits. Default [False]

Upload related parameters:

- **upload**: True or False. Default False
- **reference**: Reference of the package to upload. Ex: "zlib/1.2.8"
- **password**. Conan Password
- **remote**: Alternative remote name. Default "default"
- **stable_branch_pattern**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *stable* channel Default "master"
- **channel**: Channel where your packages will be uploaded if previous parameter doesn't match


## Environment configuration

You can also use environment variables to change the behavior of ConanMultiPackager, so you can pass no parameters in ConanMultiPackager constructor.

It's specially useful for CI integration.

- **CONAN_USERNAME**:  Your conan's username
- **CONAN_REFERENCE**: Reference of the package to upload. Ex: "zlib/1.2.8"
- **CONAN_PASSWORD**:  Conan Password
- **CONAN_REMOTE**:  Alternative remote name. Default "default"
- **CONAN_UPLOAD**: If defined will upload the generated packages
- **CONAN_GCC_VERSIONS**: Gcc versions comma separated, EX: "4.6,4.8,5.2"
- **CONAN_APPLE_CLANG_VERSIONS**: Apple clang versions comma separated, EX: "5.0,5.1"
- **CONAN_ARCHS**: Architectures to build for, comma separated, EX: "x86,x86_64"
- **CONAN_VISUAL_VERSIONS**: Visual versions, comma separated, EX: "12,14"
- **CONAN_VISUAL_RUNTIMES**: Visual runtimes, comma separated, Ex: "MT,MD"
- **CONAN_USE_DOCKER**: If defined will use docker
- **CONAN_CURRENT_PAGE**:  Current page of packages to create
- **CONAN_TOTAL_PAGES**: Total of pages
- **CONAN_DOCKER_IMAGE**: If defined and docker is being used, it will use this dockerimage instead of the default images
- **CONAN_STABLE_BRANCH_PATTERN**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *stable* channel Default "master"
- **CONAN_CHANNEL**: Channel where your packages will be uploaded if previous parameter doesn't match
- **CONAN_PIP_PACKAGE**: Specify a conan package to install (default installs the latest) e.j conan==0.0.1rc7


## Travis integration

Travis CI can generate a build with multiple jobs defining a matrix with environment variables.
We can configure the builds to be executed in the jobs defining some environment variables.

Its a real example of *.travis.yml* file that will generate packages for **Linux (gcc 4.6-5.2) and OSx for xcode6.2, xcode6.4 and xcode7.1**
It uses 2 different jobs for each compiler version

You can copy the files from this [conan-zlib repository](https://github.com/lasote/conan-zlib). Just copy the **".travis"** folder and the **".travis.yml"** file to your project and edit the latter adjusting CONAN_REFERENCE, CONAN_USERNAME and maybe the travis matrix to run more or less packages per job:


**.travis.yml**


    os: linux
    services:
       - docker
    sudo: required
    language: python
    env:
      global:
        - CONAN_UPLOAD=1
        - CONAN_REFERENCE="bzip2/1.0.6"
        - CONAN_USERNAME="lasote"
        - CONAN_CHANNEL="ci"
        - CONAN_TOTAL_PAGES=2

      matrix:
        - CONAN_GCC_VERSIONS=4.6 CONAN_CURRENT_PAGE=1 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=4.6 CONAN_CURRENT_PAGE=2 CONAN_USE_DOCKER=1

        - CONAN_GCC_VERSIONS=4.8 CONAN_CURRENT_PAGE=1 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=4.8 CONAN_CURRENT_PAGE=2 CONAN_USE_DOCKER=1

        - CONAN_GCC_VERSIONS=4.9 CONAN_CURRENT_PAGE=1 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=4.9 CONAN_CURRENT_PAGE=2 CONAN_USE_DOCKER=1

        - CONAN_GCC_VERSIONS=5.2 CONAN_CURRENT_PAGE=1 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=5.2 CONAN_CURRENT_PAGE=2 CONAN_USE_DOCKER=1

        - CONAN_GCC_VERSIONS=5.3 CONAN_CURRENT_PAGE=1 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=5.3 CONAN_CURRENT_PAGE=2 CONAN_USE_DOCKER=1

    matrix:
       include:
           - os: osx
	         osx_image: xcode7.1 # apple-clang 7.0
	         language: generic
	         env: CONAN_CURRENT_PAGE=1
           - os: osx
	         osx_image: xcode7.1 # apple-clang 7.0
	         language: generic
	         env: CONAN_CURRENT_PAGE=2

           - os: osx
	         osx_image: xcode6.4 # apple-clang 6.1
	         language: generic
	         env: CONAN_CURRENT_PAGE=1
           - os: osx
	         osx_image: xcode6.4 # apple-clang 6.1
	         language: generic
	         env: CONAN_CURRENT_PAGE=2

           - os: osx
	         osx_image: xcode6.2 # apple-clang 6.0
	         language: generic
	         env: CONAN_CURRENT_PAGE=1
           - os: osx
	         osx_image: xcode6.2 # apple-clang 6.0
	         language: generic
	         env: CONAN_CURRENT_PAGE=2

    install:
      - ./.travis/install.sh
    script:
      - ./.travis/run.sh


In case you need just one job per compiler to compile all the packages:


**.travis.yml**


    os: linux
    services:
       - docker
    sudo: required
    language: python
    env:
      global:
        - CONAN_UPLOAD=1
        - CONAN_REFERENCE="bzip2/1.0.6"
        - CONAN_USERNAME="lasote"
        - CONAN_CHANNEL="ci"
        - CONAN_TOTAL_PAGES=1
        - CONAN_CURRENT_PAGE=1

      matrix:
        - CONAN_GCC_VERSIONS=4.6 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=4.8 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=4.9 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=5.2 CONAN_USE_DOCKER=1
        - CONAN_GCC_VERSIONS=5.3 CONAN_USE_DOCKER=1
    matrix:
       include:
           - os: osx
	         osx_image: xcode7.1 # apple-clang 7.0
	         language: generic
     		 env:
           - os: osx
	         osx_image: xcode6.4 # apple-clang 6.1
	         language: generic
	         env:
           - os: osx
	         osx_image: xcode6.2 # apple-clang 6.0
	         language: generic
			 env:
    install:
      - ./.travis/install.sh
    script:
      - ./.travis/run.sh



**.travis/install.sh**

    #!/bin/bash

	set -e
	set -x

	if [[ "$(uname -s)" == 'Darwin' ]]; then
	    brew update || brew update
	    brew outdated pyenv || brew upgrade pyenv
	    brew install pyenv-virtualenv

	    if which pyenv > /dev/null; then
		eval "$(pyenv init -)"
	    fi

	    pyenv install 2.7.10
	    pyenv virtualenv 2.7.10 conan
	    pyenv rehash
	    pyenv activate conan
	fi

	pip install conan_package_tools # It install conan too
	conan user



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


Remember to set CONAN_PASSWORD variable in travis build backoffice!


## Appveyor integration

Its very similar to Travis CI, with the same **build.py** script we have the following **appveyor.yml** file:

    build: false
    environment:
        PYTHON: "C:\\Python27-x64"
        PYTHON_VERSION: "2.7.11"
        PYTHON_ARCH: "64"

        CONAN_UPLOAD: 1
        CONAN_REFERENCE: "bzip2/1.0.6"
        CONAN_USERNAME: "lasote"
        CONAN_CHANNEL: "ci"
        CONAN_TOTAL_PAGES: 4

        matrix:
            - CONAN_CURRENT_PAGE: 1
            - CONAN_CURRENT_PAGE: 2  
            - CONAN_CURRENT_PAGE: 3
            - CONAN_CURRENT_PAGE: 4
    install:
      - set PATH=%PATH%;%PYTHON%/Scripts/
      - pip.exe install conan_package_tools # It install conan too
      - conan user # It creates the conan data directory

    test_script:
      - C:\Python27-x64\python build.py



- Remember to set **CONAN_PASSWORD** variable in appveyor build backoffice!

## Bamboo CI integration

[Bamboo](https://www.atlassian.com/software/bamboo) is a commercial CI tool developed by Atlassian.
When building from bamboo several environement variables get set during builds.

If the env var **bamboo_buildNumber** is set and the branch name (**bamboo_planRepository_branch** env var) matches **stable_branch_pattern** then the channel name gets set to ```stable```.

## Jenkins CI integration

[Jenkins](https://jenkins.io/) is an open source CI tool that was originally forked from hudson.
When building from jenkins several environement variables get set during builds.
 
If the env var **JENKINS_URL** is set and the branch name (**BRANCH_NAME** env var) matches **stable_branch_pattern** then the channel name gets set to ```stable```.

Currently only the pipeline builds set the **BRANCH_NAME** env var automatically.

# Full example

You can see the full zlib example [here](https://github.com/lasote/conan-zlib)
