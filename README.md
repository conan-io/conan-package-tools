# Conan Package Tools

This package makes easy the generation of multiple packages using [conan package manager](http://conan.io).

Also ease the integration with  [TravisCI](https://travis-ci.org/) and [Appveyor](http://www.appveyor.com/) and allows to automate the package creation in CI servers and the upload to [conan](http://conan.io).

**Features**:

- Easy definition of packages that will be created.
- Paginate the packages creation, you can split the build in some different tasks (ideal for CI).
- You can use automatically Docker for auto generate packages for gcc 4.6, 4.8, 4.9, 5.2, 5.3 in a clean environment every time.
- For Windows Visual Studio builds, auto detect visual version and prepare the environment to point to that compiler.
- Upload packages directly to conan.io (or your custom conan server)
- Great and easy integration with [TravisCI](https://travis-ci.org/) and [Appveyor](http://www.appveyor.com/)


## Install

    $ pip install conan_package_tools


Or you can [clone this repository](http://github.com/conan-io/conan-package-tools) and store its location to PYTHONPATH.


## Basic Usage

First is assumes that you are creating a conan's package. 
You must have a **conanfile.txt** file and a **test** folder in your current directory and **conan test** command must work.
If you don't have it ready, take a look to [Automatically creating and testing packages](http://docs.conan.io/en/latest/packaging/testing.html)

In your **test/conanfile.py** you need to make a small adjustement, the require (current library) needs to be configurable with environment variables:


```
    channel = os.getenv("CONAN_CHANNEL", "testing")
    username = os.getenv("CONAN_USERNAME", "myuser")
    
    class DefaultNameConan(ConanFile):
        ...
        requires = "zlib/1.2.8@%s/%s" % (username, channel)
        ...

```

Instance a **ConanMultiPackager** and add builds:

```python
    from conan.packager import ConanMultiPackager

    builder = ConanMultiPackager(args, username, channel)

```

Add some package's configuration to builder (settings and options):

```python
    builder.add({"arch": "x86", "build_type": "Release"}, {"mypackage:option1": "ON"})
    builder.add({"arch": "x86_64", "build_type": "Release"}, {"mypackage:option1": "ON"})
    builder.add({"arch": "x86", "build_type": "Debug"}, {"mypackage:option2": "OFF", "mypackage:shared": True})
    
    
```

Call *pack* or *docker_pack*:

```python
    builder.pack() # Builds in current machine
    # Or
    builder.docker_pack() # Builds by default in "virtual machines" with gcc 4.6, 4.8, 4.9, 5.2 and 5.3 

```

When the builder detect a "Visual Studio" compiler and its version, will automatically configure the execution environment of the "conan test" command with the **vcvarsall.bat** script (provided by all Microsoft Visual Studio versions).
So you can compile your project with the right compiler automatically, even without CMake.

## Pagination

You can launch partial builds passing two pagination parameters, **curpage** and **total_pages**.
It's very useful with CI servers like Travis, because you can split the builds in pages just passing some parameters:

```python
    builder.pack(curpage=1, total_pages=10)

```

If you added 10 package's to the builder, each page will execute 1 package generation.


## Docker pack

Docker pack will launch N containers with a virtualized versions of Ubuntu. We have available different images, for gcc versions 4.6, 4.8, 4.9, 5.2 and 5.3
The containers will share the conan storage directory, so the packages will be generated in your conan's directory.
You can specify a subset of gcc versions and the pagination is also available:

```python
    builder.docker_pack(curpage=1, total_pages=10, gcc_versions=["4.8", "5.3"])

```

**Note**:  The package builds that will be executed in Docker should not specify the setting "compiler" nor the "compiler.version", conan will detect the available in the current system.
   
## Upload packages

```python

    builder.upload_packages("mypackage/1.2.3@user/testing", "myconanserverpassword")

```

You can pass another remote name with parameter **remote**. By default it uses default remote:


```python

    builder.upload_packages("mypackage/1.2.3@user/testing", "myconanserverpassword", remote="mycustomserver")

```


## Travis integration

Travis CI can generate a build with multiple jobs defining a matrix with environment variables.
We can configure the buils to be executed in the jobs defining some environment variables.
Its a real example of *.travis.yml* file:

```yml
    language: python
    sudo: required
    services:
      - docker
    env:
     global:
       - CONAN_UPLOAD: 1
       - CONAN_REFERENCE: "zlib/1.2.8"
       - CONAN_USERNAME: "lasote"
       - CONAN_CHANNEL: "ci"
       - CONAN_TOTAL_PAGES: 2
       - CONAN_USE_DOCKER: 1
     matrix:
       - CONAN_GCC_VERSIONS: 4.6 CONAN_CURRENT_PAGE: 1
       - CONAN_GCC_VERSIONS: 4.6 CONAN_CURRENT_PAGE: 2
       - CONAN_GCC_VERSIONS: 4.8 CONAN_CURRENT_PAGE: 1
       - CONAN_GCC_VERSIONS: 4.8 CONAN_CURRENT_PAGE: 2
       - CONAN_GCC_VERSIONS: 4.9 CONAN_CURRENT_PAGE: 1
       - CONAN_GCC_VERSIONS: 4.9 CONAN_CURRENT_PAGE: 2
       - CONAN_GCC_VERSIONS: 5.2 CONAN_CURRENT_PAGE: 1
       - CONAN_GCC_VERSIONS: 5.2 CONAN_CURRENT_PAGE: 2
       - CONAN_GCC_VERSIONS: 5.3 CONAN_CURRENT_PAGE: 1
       - CONAN_GCC_VERSIONS: 5.3 CONAN_CURRENT_PAGE: 2

    install:
      - pip install conan_package_tools # It install conan too
      - conan user # It creates the conan data directory
    script:
      - python build.py


```

Travis will launch 2 jobs per gcc version, so 10 jobs will be launched in the same build (10 different virtual machines).

Travis will launch a **build.py** python script like the below, you can use almost the same for your project, just adjust the defaults, option name and the configurations that are added to the builder object.


```python

import os
from conan.packager import ConanMultiPackager
import sys
import platform
from copy import copy


if __name__ == "__main__":
    channel = os.getenv("CONAN_CHANNEL", "testing")
    username = os.getenv("CONAN_USERNAME", "lasote")
    current_page = os.getenv("CONAN_CURRENT_PAGE", "1")
    total_pages = os.getenv("CONAN_TOTAL_PAGES", "1")
    gcc_versions = os.getenv("CONAN_GCC_VERSIONS", None)
    gcc_versions = gcc_versions.split(",") if gcc_versions else None
    use_docker = os.getenv("CONAN_USE_DOCKER", False)
    upload = os.getenv("CONAN_UPLOAD", False)
    reference = os.getenv("CONAN_REFERENCE")
    password = os.getenv("CONAN_PASSWORD")
    travis = os.getenv("TRAVIS", False)
    travis_branch = os.getenv("TRAVIS_BRANCH", None)
    appveyor = os.getenv("APPVEYOR", False)
    appveyor_branch = os.getenv("APPVEYOR_REPO_BRANCH", None)
    
    if travis:
        if travis_branch=="master":
            channel = "stable"
        else:
            channel = channel
        os.environ["CONAN_CHANNEL"] = channel
        
    if appveyor:
        if appveyor_branch=="master" and not os.getenv("APPVEYOR_PULL_REQUEST_NUMBER"):
            channel = "stable"
        else:
            channel = channel
        os.environ["CONAN_CHANNEL"] = channel
    
    args = " ".join(sys.argv[1:])
    builder = ConanMultiPackager(args, username, channel)
    builder.add_common_builds(shared_option_name="zlib:shared", visual_versions=[10, 12, 14])
    print(builder.builds)
    
    if use_docker:  
        builder.docker_pack(current_page, total_pages, gcc_versions)
    else:
        builder.pack(current_page, total_pages)
    
    if upload and reference and password:
        builder.upload_packages(reference, password)

```

- The above script uses **add_common_builds** method, that method adds the most common build configurations for windows and linux/osx. There is an optional parameter **shared_option_name** if you have an option to control the static/shared library.

    Linux/OSx:
    ```
    [{'arch': 'x86', 'build_type': 'Debug'}, {'zlib:shared': True}], 
    [{'arch': 'x86', 'build_type': 'Release'}, {'zlib:shared': True}], 
    [{'arch': 'x86', 'build_type': 'Debug'}, {'zlib:shared': False}], 
    [{'arch': 'x86', 'build_type': 'Release'}, {'zlib:shared': False}], 
    [{'arch': 'x86_64', 'build_type': 'Debug'}, {'zlib:shared': True}], 
    [{'arch': 'x86_64', 'build_type': 'Release'}, {'zlib:shared': True}], 
    [{'arch': 'x86_64', 'build_type': 'Debug'}, {'zlib:shared': False}], 
    [{'arch': 'x86_64', 'build_type': 'Release'}, {'zlib:shared': False}]]
    ```
    
    Windows (for each visual studio specified):
    ```
    [{'compiler.version': 10, 'arch': 'x86', 'build_type': 'Release', 'compiler.runtime': 'MT', 'compiler': 'Visual Studio'}, {'zlib:shared': False}],
    [{'compiler.version': 10, 'arch': 'x86', 'build_type': 'Debug', 'compiler.runtime': 'MTd', 'compiler': 'Visual Studio'}, {'zlib:shared': False}], 
    [{'compiler.version': 10, 'arch': 'x86', 'build_type': 'Debug', 'compiler.runtime': 'MDd', 'compiler': 'Visual Studio'}, {'zlib:shared': False}], 
    [{'compiler.version': 10, 'arch': 'x86', 'build_type': 'Release', 'compiler.runtime': 'MD', 'compiler': 'Visual Studio'}, {'zlib:shared': False}], 
    [{'compiler.version': 10, 'arch': 'x86', 'build_type': 'Debug', 'compiler.runtime': 'MDd', 'compiler': 'Visual Studio'}, {'zlib:shared': True}], 
    [{'compiler.version': 10, 'arch': 'x86', 'build_type': 'Release', 'compiler.runtime': 'MD', 'compiler': 'Visual Studio'}, {'zlib:shared': True}], 
    [{'compiler.version': 10, 'arch': 'x86_64', 'build_type': 'Release', 'compiler.runtime': 'MT', 'compiler': 'Visual Studio'}, {'zlib:shared': False}],
    [{'compiler.version': 10, 'arch': 'x86_64', 'build_type': 'Debug', 'compiler.runtime': 'MTd', 'compiler': 'Visual Studio'}, {'zlib:shared': False}], 
    [{'compiler.version': 10, 'arch': 'x86_64', 'build_type': 'Debug', 'compiler.runtime': 'MDd', 'compiler': 'Visual Studio'}, {'zlib:shared': False}], 
    [{'compiler.version': 10, 'arch': 'x86_64', 'build_type': 'Release', 'compiler.runtime': 'MD', 'compiler': 'Visual Studio'}, {'zlib:shared': False}], 
    [{'compiler.version': 10, 'arch': 'x86_64', 'build_type': 'Debug', 'compiler.runtime': 'MDd', 'compiler': 'Visual Studio'}, {'zlib:shared': True}], 
    [{'compiler.version': 10, 'arch': 'x86_64', 'build_type': 'Release', 'compiler.runtime': 'MD', 'compiler': 'Visual Studio'}, {'zlib:shared': True}]
    ```
    

  This method is just a helper, you can add, delete or modify the values or, like we saw previously, add the configurations with **builder.add** method.
  Just access to **builder.builds** variable and alter what you want.
  
  **Example**, use the default builds **adding a new option** and **removing** the builds with **arch x86**:
  
  ```python
  
    builder = ConanMultiPackager(args, username, channel)
    builder.add_common_builds(package_name="zlib", shared_option_name="shared")
  
    new_builds = []
    for build in builder.builds:
        new_build = copy(build)
        settings, options = new_build
        options["new_option"] = True
        if settings["arch"] != "x86":
            new_builds.append(new_build)
      
    builder.builds = new_builds
  ```
  
- The **CONAN_PASSWORD** variable is setted in Travis CI backoffice as a hidden environment variable to protect our conan.io account password. The password is used to upload the packages.

- The channel of uploaded packages will be "stable" if we are pushing out project to master branch and the default for another branch.
So we can work with a common **git flow** in out project, opening release branches and see if packaging is working, then when we push to master the packages will automatically be published to conan.io


## Appveyor integration

Its very similar to Travis CI, with the same **build.py** script we have the following **appveyor.yml** file:

```python

build: false
environment:
    PYTHON: "C:\\Python27"
    PYTHON_VERSION: "2.7.8"
    PYTHON_ARCH: "32"
    
    CONAN_UPLOAD: 1
    CONAN_REFERENCE: "zlib/1.2.8"
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
  - python build.py
  
```


# Full example

You can see the full zlib example [here](https://github.com/lasote/conan-zlib)


