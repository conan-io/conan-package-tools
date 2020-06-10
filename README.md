[![Build Status Travis](https://travis-ci.org/conan-io/conan-package-tools.svg?branch=master)](https://travis-ci.org/conan-io/conan-package-tools)
[![Build status Appveyor](https://ci.appveyor.com/api/projects/status/github/conan-io/conan-package-tools?svg=true)](https://ci.appveyor.com/project/ConanCIintegration/conan-package-tools)
[![codecov](https://codecov.io/gh/conan-io/conan-package-tools/branch/master/graph/badge.svg)](https://codecov.io/gh/conan-io/conan-package-tools)
![PyPI - Downloads](https://img.shields.io/pypi/dm/conan-package-tools.svg?style=plastic)

# Conan Package Tools


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

    from cpt.packager import ConanMultiPackager

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
    from cpt.packager import ConanMultiPackager

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

	from cpt.packager import ConanMultiPackager

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


    from cpt.packager import ConanMultiPackager

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

    from cpt.packager import ConanMultiPackager

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
- **visual_runtimes**: Generate only build configurations for the specified runtimes. (only for Visual Studio)
- **visual_toolsets**: Specify the toolsets per each specified Visual Studio version. (only for Visual Studio)
- **apple_clang_versions**: Generate only build configurations for the specified apple clang versions (Ignored if the current machine is not OSX)
- **archs**: Generate build configurations for the specified architectures, by default, ["x86", "x86_64"].
- **build_types**: Generate build configurations for the specified build_types, by default ["Debug", "Release"].

Or you can adjust environment variables:

- **CONAN_GCC_VERSIONS**
- **CONAN_VISUAL_VERSIONS**
- **CONAN_VISUAL_RUNTIMES**
- **CONAN_VISUAL_TOOLSETS**
- **CONAN_APPLE_CLANG_VERSIONS**
- **CONAN_CLANG_VERSIONS**
- **CONAN_ARCHS**
- **CONAN_BUILD_TYPES**

Check the **REFERENCE** section to see all the parameters and **ENVIRONMENT VARIABLES** available.


---
**IMPORTANT!** Both the constructor parameters and the corresponding environment variables of the previous list ONLY have effect when using `builder.add_common_builds()`.

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

- **shared_option_name**: If your conanfile.py have an option **shared**, the generated builds will contain automatically the "True/False" combination for that option.
  Pass "False" to deactivate it or "lib_name:shared_option_name" to specify a custom option name, e.j: boost:my_shared``
- **dll_with_static_runtime**: Will add also the combination of runtime MT with shared libraries.
- **header_only**: If your conanfile.py have an option **header_only**, the generated builds will contain automatically the "True/False" combination for that option [#454](https://github.com/conan-io/conan-package-tools/issues/454).
- **build_all_options_values**: It includes all possible values for the listed options [#457](https://github.com/conan-io/conan-package-tools/issues/457).

```
from cpt.packager import ConanMultiPackager

if __name__ == "__main__":
    builder = ConanMultiPackager()
    builder.add_common_builds(shared_option_name="mypackagename:shared", pure_c=False)
    builder.run()
```

## Filtering or modifying the configurations


Use the `remove_build_if` helper with a lambda function to filter configurations:


    from cpt.packager import ConanMultiPackager

    builder = ConanMultiPackager(username="myuser")
    builder.add_common_builds()
    builder.remove_build_if(lambda build: build.settings["compiler.version"] == "4.6" and build.settings["build_type"] == "Debug")

Use the `update_build_if` helper with a lambda function to alter configurations:


    from cpt.packager import ConanMultiPackager

    builder = ConanMultiPackager(username="myuser")
    builder.add_common_builds()
    builder.update_build_if(lambda build: build.settings["os"] == "Windows",
                            new_build_requires={"*": ["7zip_installer/0.1.0@conan/stable"]})
    # Also avaiable parameters:
    #    new_settings, new_options, new_env_vars, new_build_requires, new_reference


Or you can directly iterate the builds to do any change. EX: Remove the GCC 4.6 packages with build_type=Debug:

    from cpt.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(username="myuser")
        builder.add_common_builds()
        filtered_builds = []
        for settings, options, env_vars, build_requires, reference in builder.items:
            if settings["compiler.version"] != "4.6" and settings["build_type"] != "Debug":
                 filtered_builds.append([settings, options, env_vars, build_requires, reference])
        builder.builds = filtered_builds
        builder.run()


## Package Version based on Commit Checksum

Sometimes you want to use Conan as [in-source](https://docs.conan.io/en/latest/creating_packages/package_repo.html) but you do not need to specify a version in the recipe, it could be configured by your build environment. Usually you could use the branch name as the package version, but if you want to create unique packages for each new build, upload it and do not override on your remote, you will need to use a new version for each build. In this case, the branch name will not be enough, so a possible approach is to use your current commit checksum as version:


    from cpt.packager import ConanMultiPackager
    from cpt.ci_manager import CIManager
    from cpt.printer import Printer


    if __name__ == "__main__":
        printer = Printer()
        ci_manager = CIManager(printer)
        builder = ConanMultiPackager(reference="mypackage/{}".format(ci_manager.get_commit_id()[:7]))
        builder.add_common_builds()
        builder.run()

As SHA-1 is 40 digits long, you could format the result to short size

## Save created packages summary
In case you want to integrate CPT with other tools, for example you want to have build logic after creating packages, you can save a json report about all configurations and packages.

**Examples**:

    from cpt.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager()
        builder.add_common_builds()
        builder.run(summary_file='cpt_summary_file.json')


    from cpt.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager()
        builder.add_common_builds()
        builder.run()
        builder.save_packages_summary('cpt_summary_file.json')


Alternatively you can use the `CPT_SUMMARY_FILE` environment variable to set the summary file path

## Using all values for custom options
Sometimes you want to include more options to your matrix, including all possible combinations, so that, you can use **build_all_options_values**:

    from cpt.packager import ConanMultiPackager


    if __name__ == "__main__":
        builder = ConanMultiPackager(reference="mypackage/0.1.0")
        builder.add_common_builds(build_all_options_values=["mypackage:foo", "mypackage:bar"])
        builder.run()

Now let's say mypackage's recipe contains the follow options: *shared*, *fPIC*, *foo* and *bar*. Both *foo* and *bar* can accept **True** or **False**.
The method add_common_builds will generate a matrix including both *foo* and *bar* with all possible combinations.

## Using Docker

Instance ConanMultiPackager with the parameter **use_docker=True**, or declare the environment variable **CONAN_USE_DOCKER**:
It will launch, when needed, a container for the current build configuration that is being built (only for Linux builds).

There are docker images available for different gcc versions: 4.6, 4.8, 4.9, 5, 6, 7 and clang versions: 3.8, 3.9, 4.0.

The containers will share the conan storage directory, so the packages will be generated in your conan directory.

**Example**:


    from cpt.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager()
	    builder.add_common_builds()
	    builder.run()

And run the build.py:

    $ export CONAN_USERNAME=myuser
    $ export CONAN_GCC_VERSIONS=4.9
    $ export CONAN_DOCKER_IMAGE=conanio/gcc49
    $ export CONAN_USE_DOCKER=1
    $ python build.py


It will generate a set of build configurations (profiles) for gcc 4.9 and will run it inside a container of the ``conanio/gcc49`` image.

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

    from cpt.packager import ConanMultiPackager

	if __name__ == "__main__":
        command = "sudo apt-get -qq update && sudo apt-get -qq install -y tzdata"
	    builder = ConanMultiPackager(use_docker=True, docker_image='conanio/gcc7', docker_entry_script=command)
	    builder.add_common_builds()
	    builder.run()

Also, it's possible to run some internal script, before to build the package:

    from cpt.packager import ConanMultiPackager

    if __name__ == "__main__":
        command = "python bootstrap.py"
        builder = ConanMultiPackager(use_docker=True, docker_image='conanio/gcc7', docker_entry_script=command)
        builder.add_common_builds()
        builder.run()

### Using with your own Docker images
The default location inside the Docker container is `/home/conan` on Linux and
`C:\Users\ContainerAdministrator` on Windows. This is fine if you use the conan
Docker images but if you are using your own image, these locations probably won't
exist.

To use a different location, you can use the option `docker_conan_home` or the
environment variable `CONAN_DOCKER_HOME`.

### Installing extra python packages before to build

Maybe you need to install some python packages using pip before to build your conan package. To solve this situation
you could use **pip_install**:

**Example**:

This example installs bincrafters-package-tools and conan-promote before to build:

    from cpt.packager import ConanMultiPackager

    if __name__ == "__main__":
        builder = ConanMultiPackager(pip_install=["bincrafters-package-tools==0.17.0", "conan-promote==0.1.2"])
        builder.add_common_builds()
        builder.run()

But if you prefer to use environment variables:

    export CONAN_PIP_INSTALL="bincrafters-package-tools==0.17.0,conan-promote=0.1.2"

### Passing additional Docker parameters during build
When running `conan create` step in Docker, you might want to run the container with a different Docker network. For this you can use `docker_run_options` parameter (or `CONAN_DOCKER_RUN_OPTIONS` envvar)

    builder = ConanMultiPackager(
      docker_run_options='--network bridge --privileged',
      ...

When run, this will translate to something like this:

    sudo -E docker run ... --network bridge --privileged conanio/gcc6 /bin/sh -c "cd project &&  run_create_in_docker"


### Installing custom Conan config

To solve custom profiles and remotes, Conan provides the [config](https://docs.conan.io/en/latest/reference/commands/consumer/config.html) feature where is possible to edit the conan.conf or install config files.

If you need to run `conan config install <url>` before to build there is the argument `config_url` in CPT:

    from cpt.packager import ConanMultiPackager

    if __name__ == "__main__":
        config_url = "https://github.com/bincrafters/conan-config.git"
        builder = ConanMultiPackager(config_url=config_url)
        builder.add_common_builds()
        builder.run()

But if you are not interested to update your build.py script, it's possible to use environment variables instead:

    export CONAN_CONFIG_URL=https://github.com/bincrafters/conan-config.git

## Specifying a different base profile

The options, settings and environment variables that the ``add_common_builds()`` method generate, are applied into the `default` profile
of the conan installation. If you want to use a different profile you can pass the name of the profile in the ``run()`` method.


 **Example**:


    from cpt.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager(clang_versions=["3.8", "3.9"])
	    builder.add_common_builds()
	    builder.run("myclang")

Alternatively you can use the `CONAN_BASE_PROFILE` environment variable to choose a different base profile:

    CONAN_BASE_PROFILE=myclang

# The CI integration

If you are going to use a CI server to generate different binary packages for your recipe, the best approach is to control
the build configurations with environment variables.

So, having a generic ``build.py`` should be enough for almost all the cases:


    from cpt.packager import ConanMultiPackager

	if __name__ == "__main__":
	    builder = ConanMultiPackager()
	    builder.add_common_builds(shared_option_name="mypackagename:shared", pure_c=False)
	    builder.run()

Then, in your CI configuration, you can declare different environment variables to limit the build configurations to an specific compiler version,
using a specific docker image etc.

For example, if you declare the following environment variables:

    CONAN_GCC_VERSIONS=4.9
    CONAN_DOCKER_IMAGE=conanio/gcc49

the ``add_common_builds()`` method will only add different build configurations for GCC=4.9 and will run them in a docker container.

You can see working integrations with Travis and Appveyor in the zlib repository [here](https://github.com/conan-community/conan-zlib)


## Travis integration

Travis CI can generate a build with multiple jobs defining a matrix with environment variables.
We can configure the builds to be executed in the jobs by defining some environment variables.

The following is a real example of a **.travis.yml** file that will generate packages for Linux gcc (4.9, 5, 6), Linux Clang (3.9 and 4.0) and OSx with apple-clang (8.0, 8.1 and 9.0).

Remember, you can use `conan new` command to generate the base files for appveyor, travis etc. Check `conan new --help`.


**.travis.yml** example:


    env:
       global:
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
            env: CONAN_GCC_VERSIONS=4.9 CONAN_DOCKER_IMAGE=conanio/gcc49
          - <<: *linux
            env: CONAN_GCC_VERSIONS=5 CONAN_DOCKER_IMAGE=conanio/gcc5
          - <<: *linux
            env: CONAN_GCC_VERSIONS=6 CONAN_DOCKER_IMAGE=conanio/gcc6
          - <<: *linux
            env: CONAN_GCC_VERSIONS=7 CONAN_DOCKER_IMAGE=conanio/gcc7
          - <<: *linux
            env: CONAN_CLANG_VERSIONS=3.9 CONAN_DOCKER_IMAGE=conanio/clang39
          - <<: *linux
            env: CONAN_CLANG_VERSIONS=4.0 CONAN_DOCKER_IMAGE=conanio/clang40
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
            env: CONAN_GCC_VERSIONS=4.9 CONAN_DOCKER_IMAGE=conanio/gcc49 CONAN_CURRENT_PAGE=1

          - <<: *linux
            env: CONAN_GCC_VERSIONS=4.9 CONAN_DOCKER_IMAGE=conanio/gcc49 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_GCC_VERSIONS=5 CONAN_DOCKER_IMAGE=conanio/gcc5 CONAN_CURRENT_PAGE=1

           - <<: *linux
            env: CONAN_GCC_VERSIONS=5 CONAN_DOCKER_IMAGE=conanio/gcc5 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_GCC_VERSIONS=6 CONAN_DOCKER_IMAGE=conanio/gcc6 CONAN_CURRENT_PAGE=1

          - <<: *linux
            env: CONAN_GCC_VERSIONS=6 CONAN_DOCKER_IMAGE=conanio/gcc6 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_CLANG_VERSIONS=3.9 CONAN_DOCKER_IMAGE=conanio/clang39 CONAN_CURRENT_PAGE=1

           - <<: *linux
            env: CONAN_CLANG_VERSIONS=3.9 CONAN_DOCKER_IMAGE=conanio/clang39 CONAN_CURRENT_PAGE=2

          - <<: *linux
            env: CONAN_CLANG_VERSIONS=4.0 CONAN_DOCKER_IMAGE=conanio/clang40 CONAN_CURRENT_PAGE=1

          - <<: *linux
            env: CONAN_CLANG_VERSIONS=4.0 CONAN_DOCKER_IMAGE=conanio/clang40 CONAN_CURRENT_PAGE=2

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


## Upload dependencies ([#237](https://github.com/conan-io/conan-package-tools/issues/237))

Sometimes your dependencies are not available in remotes and you need to pass ``--build=missing`` to build them.
The problem is that you will need to fix one-by-one, updating the CI script, instead of just uploading all built packages.

Now you can upload **ALL** of your dependencies together, in addition to your package, to the same remote. To do this, you need to define:

    CONAN_UPLOAD_DEPENDENCIES="all"

Or, set it in ``ConanMultiPackager`` arguments:

    ConanMultiPackager(upload_dependencies="all")

However, maybe you want to upload **ONLY** specified packages by their names:

    CONAN_UPLOAD_DEPENDENCIES="foo/0.1@user/channel,bar/1.2@bar/channel"

Or,

    ConanMultiPackager(upload_dependencies=["foo/0.1@user/channel", "bar/1.2@bar/channel"])

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

    from cpt.packager import ConanMultiPackager
    from collections import defaultdict

    if __name__ == '__main__':
        builder = ConanMultiPackager(curpage="x86", total_pages=2)
        named_builds = defaultdict(list)
        builder.add_common_builds(shared_option_name="bzip2:shared", pure_c=True)
        for settings, options, env_vars, build_requires, reference in builder.items:
            named_builds[settings['arch']].append([settings, options, env_vars, build_requires, reference])
        builder.named_builds = named_builds
        builder.run()

named_builds now have a dictionary entry for x86 and another for x86_64:

- for **CONAN_CURRENT_PAGE="x86"** it would do all x86 builds
- for **CONAN_CURRENT_PAGE="x86_64"** it would do all x86_64 builds



### Generating multiple references for the same recipe

You can add a different reference in the builds tuple, so for example, if your recipe has no "version"
field, you could generate several versions in the same build script. Conan package tools will export
the recipe using the different reference automatically:

    from cpt.packager import ConanMultiPackager

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

    from cpt.packager import ConanMultiPackager

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

Check an example [here](https://github.com/conan-community/conan-zlib/blob/release/1.2.8/appveyor.yml)


## Clang builds

Clang compiler builds are also supported. You can use this feature with TravisCI.

You can choose different Clang compiler configurations:

- **Version**: 3.8, 3.9 and 4.0 are supported
- **Architecture**: x86 and x86_64 are supported

Using **CONAN_CLANG_VERSIONS** env variable in Travis ci or Appveyor:

    CONAN_CLANG_VERSIONS = "3.8,3.9,4.0"

# FULL REFERENCE


## ConanMultiPackager parameters reference

- **username**: The username (part of the package reference, not the login_username)
- **login_username**: The login username. Could take two possible values:

    - String with the login":

       ```
       login_username = "my_user"
       ```

    - Dict containing the remote name and the login for that remote. Use together with "remotes" variable to specify remote names e.j:

       ```
       login_username = {"remote1": "my_user", "my_artifactory": "other_user"}
       ```

- **password**. Password to authenticate with the remotes. Could take two possible values:

    - String with the password:

       ```
       password = "my_pass"
       ```

    - Dict containing the remote name and the login for that remote. Use together with "remotes" variable to specify remote names e.j:

       ```
       password = {"remote1": "my_pass", "my_artifactory": "my_pass2"}
       ```

- **remotes**: Could take two values:

    - String of URLs separated by ",":

       ```
       remotes = "https://api.bintray.com/conan/conan-community/conan,https://api.bintray.com/conan/other/conan2"
       ```

    - List of tuples containing the "url", "use_ssl" flag and "name" . e.j:

       ```
       remotes = [("https://api.bintray.com/conan/conan-community/conan", True, "remote1"),
                  ("https://api.bintray.com/conan/other/conan2", False, "remote2")]
       ```
- **options**: Options used on package build:

    - List of options:
       ```
       options = ["foobar:with_qux=True", "foobar:with_bar=False"]

       ```

- **gcc_versions**: List with a subset of gcc_versions. Default ["4.9", "5", "6", "7"]
- **clang_versions**: List with a subset of clang_versions. Default ["3.8", "3.9", "4.0"]
- **apple_clang_versions**: List with a subset of apple-clang versions. Default ["6.1", "7.3", "8.0"]
- **visual_versions**: List with a subset of Visual Studio versions. Default [10, 12, 14]
- **visual_runtimes**: List containing Visual Studio runtimes to use in builds. Default ["MT", "MD", "MTd", "MDd"]
- **mingw_configurations**: Configurations for MinGW
- **archs**: List containing specific architectures to build for. Default ["x86", "x86_64"]
- **use_docker**: Use docker for package creation in Linux systems.
- **docker_run_options**: Pass additional parameters for docker when running the create step.
- **docker_conan_home**: Location where package source files will be copied to inside the Docker container
- **docker_image_skip_update**: If defined, it will skip the initialization update of "conan package tools" and "conan" in the docker image. By default is False.
- **docker_image_skip_pull**: If defined, it will skip the "docker pull" command, enabling a local image to be used, and without being overwritten.
- **always_update_conan_in_docker**: If True, "conan package tools" and "conan" will be installed and upgraded in the docker image in every build execution.
  and the container won't be commited with the modifications.
- **docker_entry_script**: Command to be executed before to build when running Docker.
- **pip_install**: Package list to be installed by pip before to build. e.j ["foo", "bar"]
- **docker_32_images**: If defined, and the current build is arch="x86" the docker image name will be appended with "-i386". e.j: "conanio/gcc63-i386"
- **docker_shell**: Shell command to be executed by Docker. e.j: "/bin/bash -c" (Linux), "cmd /C" (Windows)
- **curpage**: Current page of packages to create
- **total_pages**: Total number of pages
- **vs10_x86_64_enabled**: Flag indicating whether or not to build for VS10 64bits. Default [False]
- **upload_retry**: Num retries in upload in case of failure.
- **upload_only_when_stable**: Will try to upload only if the channel is the stable channel. Default [False]
- **upload_only_when_tag**: Will try to upload only if the branch is a tag. Default [False]
- **upload_only_recipe**: If defined, will try to upload **only** the recipes. The built packages will **not** be uploaded. Default [False]
- **upload_dependencies**: Will try to upload dependencies to your remote. Default [False]
- **build_types**: List containing specific build types. Default ["Release", "Debug"]
- **cppstds**: List containing specific cpp standards. Default None
- **skip_check_credentials**: Conan will skip checking the user credentials before building the packages. And if no user/remote is specified, will try to upload with the
  already stored credentiales in the local cache. Default [False]
- **allow_gcc_minors** Declare this variable if you want to allow gcc >=5 versions with the minor (5.1, 6.3 etc).
- **exclude_vcvars_precommand** For Visual Studio builds, it exclude the vcvars call to set the environment.
- **build_policy**:  Can be None, single value or a list. Default None.
    -  None: Only Build current package. Equivalent to `--build current_package_ref`
    - "never": No build from sources, only download packages. Equivalent to `--build never`
    - "missing": Build only missing packages. Equivalent to `--build missing`
    - "outdated": Build only missing or if the available package is not built with the current recipe. Useful to upload new configurations, e.j packages for a new compiler without
      rebuild all packages. Equivalent to `--build outdated`
    - "all": Build all requirements. Equivalent to `--build`
    - "cascade": Build from code all the nodes with some dependency being built (for any reason). Equivalent to `--build cascade`
    - "some_package" : Equivalent to `--build some_package`
    - "pattern\*": will build only the packages with the reference starting with pattern\*. Equivalent to `--build pattern*`
    - ["pattern\*", "another_pattern\*"]: will build only the packages with the reference matching these patterns. Equivalent to `--build pattern* --build another_pattern*`
    - ["pattern\*", "outdated"]:  `--build pattern* --build outdated`
Check [Conan Build policies](https://docs.conan.io/en/latest/mastering/policies.html) for more details.
- **test_folder**: Custom test folder consumed by Conan create, e.j .conan/test_package
- **lockfile**: Custom conan lockfile to be used, e.j. conan.lock. Default [None]
- **conanfile**: Custom conanfile consumed by Conan create. e.j. conanfile.py
- **config_url**: Conan config URL be installed before to build e.j https://github.com/bincrafters/conan-config.git
- **config_args**: Conan config arguments used when installing conan config
- **force_selinux**: Force docker to relabel file objects on the shared volumes
- **skip_recipe_export**: If True, the package recipe will only be exported on the first build. Default [False]
- **update_dependencies**: Update all dependencies before building e.g conan create -u

Upload related parameters:

- **upload**: Could take two values:

    - String with an URL.
       ```
       upload = "https://api.bintray.com/conan/conan-community/conan"
       ```

    - Tuple containing the "url", "use_ssl" flag and "name".

       ```
       upload = ("https://api.bintray.com/conan/conan-community/conan", True, "remote1")
       ```

- **reference**: Reference of the package to upload. Ex: "zlib/1.2.8". If not specified it will be read from the `conanfile.py`.
- **remote**: Alternative remote name. Default "default"
- **stable_branch_pattern**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *stable* channel.
  By default it will check the following patterns: ``["master$", "release*", "stable*"]``
- **stable_channel**: Stable channel, default "stable".
- **channel**: Channel where your packages will be uploaded if previous parameter doesn't match


## Commit messages reference

The current commit message can contain special messages:

- **[skip ci]**: Will skip the building of any package (unless `CONAN_IGNORE_SKIP_CI` is set)
- **[build=XXX]**: Being XXX a build policy (see build_policy parameter reference)
- **[build=XXX] [build=YYY]**: Being XXX and YYY the two build policies to use (see build_policy parameter reference)


## Complete ConanMultiPackager methods reference:

- **add_common_builds(shared_option_name=None, pure_c=True, dll_with_static_runtime=False, reference=None, header_only=True, build_all_options_values=None)**: Generate a set of package configurations and add them to the
  list of packages that will be created.

    - **shared_option_name**: If given, ConanMultiPackager will add different configurations for -o shared=True and -o shared=False.
    - **pure_c**: ConanMultiPackager won't generate different builds for the **libstdc++** c++ standard library, because it is a pure C library.
    - **dll_with_static_runtime**: generate also build for "MT" runtime when the library is shared.
    - **reference**: Custom package reference
    - **header_only**: Generate new builds following header-only options [#454](https://github.com/conan-io/conan-package-tools/issues/454)
    - **build_all_options_values**: Include all values for the listed options [#457](https://github.com/conan-io/conan-package-tools/issues/457)

- **login(remote_name)**: Performs a `conan user` command in the specified remote.

- **add(settings=None, options=None, env_vars=None, build_requires=None)**: Add a new build configuration, so a new binary package will be built for the specified configuration.

- **run()**: Run the builds (Will invoke conan create for every specified configuration)



## Environment configuration

You can also use environment variables to change the behavior of ConanMultiPackager, so that you don't pass parameters to the ConanMultiPackager constructor.

This is especially useful for CI integration.

- **CONAN_USERNAME**: Your conan username (for the package reference)
- **CONAN_REFERENCE**: Reference of the package to upload, e.g. "zlib/1.2.8". Otherwise it will be read from the `conanfile.py`
- **CONAN_LOGIN_USERNAME**: Unique login username for all remotes. Will use "CONAN_USERNAME" when not present.
- **CONAN_LOGIN_USERNAME_XXX**: Specify a login for a remote name:

  - `CONAN_LOGIN_USERNAME_MYREPO=my_username`

- **CONAN_PASSWORD**: Conan Password, or API key if you are using Bintray.
- **CONAN_PASSWORD_XXX**: Specify a password for a remote name:

  - `CONAN_PASSWORD_MYREPO=mypassword`

- **CONAN_REMOTES**: List of URLs separated by "," for the additional remotes (read).
                     You can specify the SSL verify flag and the remote name using the "@" separator. e.j:

  - `CONAN_REMOTES=url1@True@remote_name, url2@False@remote_name2`

  The remote name is useful in case you want to specify custom credentials for different remotes. See `CONAN_LOGIN_USERNAME_XXX` and `CONAN_PASSWORD_XXX`

- **CONAN_UPLOAD**: URL of the repository where we want to use to upload the packages.
  The value can containing the URL, the SSL validation flag and remote name (last two optionals) separated by "@". e.j:

  - `CONAN_UPLOAD=https://api.bintray.com/conan/conan-community/conan`
  - `CONAN_UPLOAD=https://api.bintray.com/conan/conan-community/conan@True`
  - `CONAN_UPLOAD=https://api.bintray.com/conan/conan-community/conan@True@other_repo_name`

  If a remote name is not specified, `upload_repo` will be used as a remote name.
  If the SSL validation configuration is not specified, it will use `True` by default.

- **CONAN_UPLOAD_RETRY**: If defined, in case of fail retries to upload again the specified times
- **CONAN_UPLOAD_ONLY_WHEN_STABLE**: If defined, will try to upload the packages only when the current channel is the stable one.
- **CONAN_UPLOAD_ONLY_WHEN_TAG**: If defined, will try to upload the packages only when the current branch is a tag.
- **CONAN_UPLOAD_ONLY_RECIPE**: If defined, will try to upload **only** the recipes. The built packages will **not** be uploaded.
- **CONAN_UPLOAD_DEPENDENCIES**: If defined, will try to upload the listed package dependencies to your remote.

- **CONAN_SKIP_CHECK_CREDENTIALS**: Conan will skip checking the user credentials before building the packages. And if no user/remote is specified, will try to upload with the
  already stored credentiales in the local cache. Default [False]
- **CONAN_DOCKER_ENTRY_SCRIPT**: Command to be executed before to build when running Docker.
- **CONAN_PIP_INSTALL**: Package list to be installed by pip before to build, comma separated, e.g. "pkg-foo==0.1.0,pkg-bar"
- **CONAN_GCC_VERSIONS**: Gcc versions, comma separated, e.g. "4.6,4.8,5,6"
- **CONAN_CLANG_VERSIONS**: Clang versions, comma separated, e.g. "3.8,3.9,4.0"
- **CONAN_APPLE_CLANG_VERSIONS**: Apple clang versions, comma separated, e.g. "6.1,8.0"
- **CONAN_ARCHS**: Architectures to build for, comma separated, e.g. "x86,x86_64"
- **CONAN_OPTIONS**: Conan build options, comma separated, e.g. "foobar:with_bar=True,foobar:with_qux=False"
- **CONAN_SHARED_OPTION_NAME**: Set `shared_option_name` by environment variable, e.g. "mypackagename:shared"
- **CONAN_BUILD_ALL_OPTIONS_VALUES**: Set `build_all_options_values` by environment variable, e.g. "mypackagename:foo,mypackagename:bar"
- **CONAN_BUILD_TYPES**: Build types to build for, comma separated, e.g. "Release,Debug"
- **CONAN_CPPSTDS**: List containing values for `compiler.cppstd`. Default None
- **CONAN_VISUAL_VERSIONS**: Visual versions, comma separated, e.g. "12,14"
- **CONAN_VISUAL_RUNTIMES**: Visual runtimes, comma separated, e.g. "MT,MD"
- **CONAN_VISUAL_TOOLSETS**: Map Visual versions to toolsets, e.g. `14=v140;v140_xp,12=v120_xp`
- **CONAN_USE_DOCKER**: If defined will use docker
- **CONAN_CURRENT_PAGE**:  Current page of packages to create
- **CONAN_TOTAL_PAGES**: Total number of pages
- **CONAN_DOCKER_IMAGE**: If defined and docker is being used, it will use this dockerimage instead of the default images, e.g. "conanio/gcc63"
- **CONAN_DOCKER_HOME**: Location where package source files will be copied to inside the Docker container
- **CONAN_DOCKER_RUN_OPTIONS**: Pass additional parameters for docker when running the create step
- **CONAN_DOCKER_IMAGE_SKIP_UPDATE**: If defined, it will skip the initialization update of "conan package tools" and "conan" in the docker image. By default is False.
- **CONAN_DOCKER_IMAGE_SKIP_PULL**: If defined, it will skip the "docker pull" command, enabling a local image to be used, and without being overwritten.
- **CONAN_ALWAYS_UPDATE_CONAN_DOCKER**: If defined, "conan package tools" and "conan" will be installed and upgraded in the docker image in every build execution
  and the container won't be commited with the modifications.
- **CONAN_DOCKER_32_IMAGES**: If defined, and the current build is arch="x86" the docker image name will be appended with "-i386". e.j: "conanio/gcc63-i386"
- **CONAN_DOCKER_SHELL**: Shell command to be executed by Docker. e.j: "/bin/bash -c" (Linux), "cmd /C" (Windows)
- **CONAN_STABLE_BRANCH_PATTERN**: Regular expression, if current git branch matches this pattern, the packages will be uploaded to *CONAN_STABLE_CHANNEL* channel. Default "master". E.j: "release/*"
- **CONAN_STABLE_CHANNEL**: Stable channel name, default "stable"
- **CONAN_CHANNEL**: Channel where your packages will be uploaded if the previous parameter doesn't match
- **CONAN_PIP_PACKAGE**: Specify a conan package to install (by default, installs the latest) e.j conan==0.0.1rc7
- **MINGW_CONFIGURATIONS**: Specify a list of MinGW builds. See MinGW builds section.
- **CONAN_BASH_PATH**: Path to a bash executable. Used only in windows to help the tools.run_in_windows_bash() function to locate our Cygwin/MSYS2 bash.
  Set it with the bash executable path if it’s not in the PATH or you want to use a different one.
- **CONAN_PIP_USE_SUDO** Use "sudo" when invoking pip, by default it will use sudo when not using Windows and not running docker image "conanio/". "False" to deactivate.
- **CONAN_PIP_COMMAND** Run custom `pip` command when updating Conan. e.g. "/usr/bin/pip2"
- **CONAN_DOCKER_PIP_COMMAND** Run custom `pip` command when updating Conan and CPT in Docker container. e.g. "/usr/bin/pip2"
- **CONAN_DOCKER_USE_SUDO** Use "sudo" when invoking docker, by default it will use sudo when not using Windows. "False" to deactivate.
- **CONAN_ALLOW_GCC_MINORS** Declare this variable if you want to allow gcc >=5 versions with the minor (5.1, 6.3 etc).
- **CONAN_EXCLUDE_VCVARS_PRECOMMAND** For Visual Studio builds, it exclude the vcvars call to set the environment.
- **CONAN_BUILD_REQUIRES** You can specify additional build requires for the generated profile with an environment variable following the same profile syntax and separated by ","
  i.e ``CONAN_BUILD_REQUIRES: mingw-installer/7.1@conan/stable, pattern: other/1.0@conan/stable``
- **CONAN_BUILD_POLICY**: Comma separated list of build policies. Default None.
    -  None: Only Build current package. Equivalent to `--build current_package_ref`
    - "never": No build from sources, only download packages. Equivalent to `--build never`
    - "missing": Build only missing packages. Equivalent to `--build missing`
    - "outdated": Build only missing or if the available package is not built with the current recipe. Useful to upload new configurations, e.j packages for a new compiler without
      rebuild all packages. Equivalent to `--build outdated`
    - "all": Build all requirements. Equivalent to `--build`
    - "cascade": Build from code all the nodes with some dependency being built (for any reason). Equivalent to `--build cascade`
    - "some_package" : Equivalent to `--build some_package`
    - "pattern\*": will build only the packages with the reference starting with pattern\*. Equivalent to `--build pattern*`
    - "pattern\*,another_pattern\*": will build only the packages with the reference matching these patterns. Equivalent to `--build pattern* --build another_pattern*`
    - "pattern\*,outdated": Equivalent to `--build pattern* --build outdated`
Check [Conan Build policies](https://docs.conan.io/en/latest/mastering/policies.html) for more details.
- **CONAN_CONFIG_URL**: Conan config URL be installed before to build e.j https://github.com/bincrafters/conan-config.git
- **CONAN_CONFIG_ARGS**: Conan config arguments used when installing conan config
- **CONAN_BASE_PROFILE**: Apply options, settings, etc. to this profile instead of `default`.
- **CONAN_IGNORE_SKIP_CI**: Ignore `[skip ci]` in commit message.
- **CONAN_CONANFILE**: Custom conanfile consumed by Conan create. e.j. conanfile.py
- **CONAN_LOCKFILE**: Custom conan lockfile to be used, e.j. conan.lock.
- **CPT_TEST_FOLDER**: Custom test_package path, e.j .conan/test_package
- **CONAN_FORCE_SELINUX**: Force docker to relabel file objects on the shared volumes
- **CONAN_SKIP_RECIPE_EXPORT**: If defined, the package recipe will only be exported on the first build.
- **CPT_UPDATE_DEPENDENCIES**: Update all dependencies before building e.g conan create -u


# Full example

You can see the full zlib example [here](https://github.com/conan-community/conan-zlib)
