import subprocess
import unittest
import time
import textwrap


from conans import tools
from conans.model.ref import ConanFileReference
from conans.model.version import Version
from cpt import get_client_version
from cpt.packager import ConanMultiPackager
from cpt.test.integration.base import BaseTest, CONAN_UPLOAD_PASSWORD, CONAN_LOGIN_UPLOAD
from cpt.test.unit.utils import MockCIManager
from cpt.ci_manager import is_github_actions


def is_linux_and_have_docker():
    return tools.os_info.is_linux and tools.which("docker")


class DockerTest(BaseTest):

    CONAN_SERVER_ADDRESS = "http://0.0.0.0:9300"

    def setUp(self):
        super(DockerTest, self).setUp()
        self.server_process = subprocess.Popen("conan_server")
        time.sleep(3)

    def tearDown(self):
        self.server_process.kill()
        super(DockerTest, self).tearDown()

    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    @unittest.skipIf(is_github_actions(), "FIXME: It fails on Github Actions")
    def test_docker(self):
        client_version = get_client_version()
        ci_manager = MockCIManager()
        unique_ref = "zlib/%s" % str(time.time())
        conanfile = textwrap.dedent("""
                from conans import ConanFile
                import os

                class Pkg(ConanFile):
                    settings = "os", "compiler", "build_type", "arch"
            """)

        self.save_conanfile(conanfile)
        with tools.environment_append({"CONAN_DOCKER_RUN_OPTIONS": "--network=host --add-host=host.docker.internal:host-gateway -v{}:/tmp/cpt".format(self.root_project_folder),
                                       "CONAN_DOCKER_ENTRY_SCRIPT": "pip install -U /tmp/cpt",
                                       "CONAN_USE_DOCKER": "1",
                                       "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                                       "CONAN_LOGIN_USERNAME": "demo",
                                       "CONAN_USERNAME": "demo",
                                       "CONAN_UPLOAD": DockerTest.CONAN_SERVER_ADDRESS,
                                       "CONAN_PASSWORD": "demo"}):

            self.packager = ConanMultiPackager(channel="mychannel",
                                               gcc_versions=["8"],
                                               archs=["x86", "x86_64"],
                                               build_types=["Release"],
                                               reference=unique_ref,
                                               ci_manager=ci_manager)
            self.packager.add_common_builds()
            self.packager.run()

        search_pattern = "%s*" % unique_ref
        ref = ConanFileReference.loads("%s@demo/mychannel" % unique_ref)

        # Remove from remote
        if Version(client_version) < Version("1.7"):
            results = self.api.search_recipes(search_pattern, remote="upload_repo")["results"][0]["items"]
            self.assertEquals(len(results), 1)
            packages = self.api.search_packages(ref, remote="upload_repo")["results"][0]["items"][0]["packages"]
            self.assertEquals(len(packages), 2)
            self.api.authenticate(name=CONAN_LOGIN_UPLOAD, password=CONAN_UPLOAD_PASSWORD,
                                  remote="upload_repo")
            self.api.remove(search_pattern, remote="upload_repo", force=True)
            self.assertEquals(self.api.search_recipes(search_pattern)["results"], [])
        else:
            results = self.api.search_recipes(search_pattern, remote_name="upload_repo")["results"][0]["items"]
            self.assertEquals(len(results), 1)
            if Version(client_version) >= Version("1.12.0"):
                ref = repr(ref)
            packages = self.api.search_packages(ref, remote_name="upload_repo")["results"][0]["items"][0]["packages"]
            self.assertEquals(len(packages), 2)
            self.api.authenticate(name="demo", password="demo",
                                  remote_name="upload_repo")
            self.api.remove(search_pattern, remote_name="upload_repo", force=True)
            self.assertEquals(self.api.search_recipes(search_pattern)["results"], [])

        # Try upload only when stable, shouldn't upload anything
        with tools.environment_append({"CONAN_DOCKER_RUN_OPTIONS": "--network=host -v{}:/tmp/cpt".format(self.root_project_folder),
                                       "CONAN_DOCKER_ENTRY_SCRIPT": "pip install -U /tmp/cpt",
                                       "CONAN_USE_DOCKER": "1",
                                       "CONAN_LOGIN_USERNAME": "demo",
                                       "CONAN_USERNAME": "demo",
                                       "CONAN_PASSWORD": "demo",
                                       "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                                       "CONAN_UPLOAD_ONLY_WHEN_STABLE": "1"}):
            self.packager = ConanMultiPackager(channel="mychannel",
                                               gcc_versions=["8"],
                                               archs=["x86", "x86_64"],
                                               build_types=["Release"],
                                               reference=unique_ref,
                                               upload=DockerTest.CONAN_SERVER_ADDRESS,
                                               ci_manager=ci_manager)
            self.packager.add_common_builds()
            self.packager.run()

        if Version(client_version) < Version("1.7"):
            results = self.api.search_recipes(search_pattern, remote="upload_repo")["results"]
            self.assertEquals(len(results), 0)
            self.api.remove(search_pattern, remote="upload_repo", force=True)
        else:
            results = self.api.search_recipes(search_pattern, remote_name="upload_repo")["results"]
            self.assertEquals(len(results), 0)
            self.api.remove(search_pattern, remote_name="upload_repo", force=True)

    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    @unittest.skipIf(is_github_actions(), "FIXME: It fails on Github Actions")
    def test_docker_run_options(self):
        conanfile = textwrap.dedent("""
                from conans import ConanFile
                import os

                class Pkg(ConanFile):
                    settings = "os", "compiler", "build_type", "arch"
                    requires = "zlib/1.2.11"

                    def build(self):
                        pass
            """)
        self.save_conanfile(conanfile)
        # Validate by Environemnt Variable
        with tools.environment_append({"CONAN_DOCKER_ENTRY_SCRIPT": "pip install -U /tmp/cpt",
                                       "CONAN_USERNAME": "bar",
                                       "CONAN_DOCKER_IMAGE": "conanio/gcc8",
                                       "CONAN_REFERENCE": "foo/0.0.1@bar/testing",
                                       "CONAN_DOCKER_RUN_OPTIONS": "--network=host, --add-host=google.com:8.8.8.8 -v{}:/tmp/cpt".format(self.root_project_folder),
                                       "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                                       "CONAN_FORCE_SELINUX": "TRUE",
                                       "CONAN_DOCKER_SHELL": "/bin/bash -c"
                                       }):
            self.packager = ConanMultiPackager(gcc_versions=["8"],
                                               archs=["x86_64"],
                                               build_types=["Release"],
                                               out=self.output.write)
            self.packager.add({})
            self.packager.run()
            self.assertIn("--network=host --add-host=google.com:8.8.8.8 -v", self.output)
            self.assertIn("/bin/bash -c", self.output)
            self.assertIn("/home/conan/project:z", self.output)

        # Validate by parameter
        with tools.environment_append({"CONAN_USERNAME": "bar",
                                       "CONAN_DOCKER_IMAGE": "conanio/gcc8",
                                       "CONAN_REFERENCE": "foo/0.0.1@bar/testing",

                                       }):

            self.packager = ConanMultiPackager(gcc_versions=["8"],
                                               archs=["x86_64"],
                                               build_types=["Release"],
                                               docker_run_options="--network=host -v{}:/tmp/cpt --cpus=1".format(self.root_project_folder) ,
                                               docker_entry_script="pip install -U /tmp/cpt",
                                               docker_image_skip_update=True,
                                               docker_shell="/bin/bash -c",
                                               out=self.output.write,
                                               force_selinux=True)
            self.packager.add({})
            self.packager.run()
            self.assertIn("--cpus=1  conanio/gcc8", self.output)
            self.assertIn("/bin/bash -c", self.output)
            self.assertIn("/home/conan/project:z", self.output)

    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    @unittest.skipIf(is_github_actions(), "FIXME: It fails on Github Actions")
    def test_docker_run_android(self):
        self.create_project()
        command = ('docker run --rm -v "{}:/home/conan/project" ',
                   '-e CONAN_RECIPE_LINTER="False" ',
                   '-e CONAN_PIP_PACKAGE="0" ',
                   '-e CONAN_DOCKER_ENTRY_SCRIPT="pip install -U /tmp/cpt" ',
                   '-e CONAN_USERNAME="bar" ',
                   '-e CONAN_DOCKER_IMAGE="conanio/android-clang8" ',
                   '-e CONAN_CHANNEL="testing" ',
                   '-e CONAN_DOCKER_RUN_OPTIONS="-v{}:/tmp/cpt" ',
                   '-e CONAN_DOCKER_IMAGE_SKIP_UPDATE="TRUE" ',
                   '-e CONAN_DOCKER_USE_SUDO="FALSE" ',
                   '-e CONAN_ARCHS="x86_64" ',
                   '-e CONAN_CLANG_VERSIONS="8" ',
                   '-e CONAN_BUILD_TYPES="Release" ',
                   '-e CONAN_LOGIN_USERNAME="bar" ',
                   '-e CONAN_REFERENCE="hello/0.1.0@bar/testing" ',
                   '-e CPT_PROFILE="@@include(default)@@@@[settings]@@arch=x86_64@@build_type=Release@@compiler=clang@@compiler.version=8@@[options]@@@@[env]@@@@[build_requires]@@@@" ',
                   '-e CONAN_TEMP_TEST_FOLDER="1" ',
                   '-e CPT_UPLOAD_RETRY="3" ',
                   '-e CPT_CONANFILE="conanfile.py" ',
                   '-v{}:/tmp/cpt  ',
                   'conanio/android-clang8 ',
                   '/bin/sh -c " cd project &&  pip install -U /tmp/cpt && run_create_in_docker "')
        command = "".join(command).format(self.tmp_folder, self.root_project_folder, self.root_project_folder)
        output = subprocess.check_output(command, shell=True).decode()
        self.assertIn("os=Android", output)
        self.assertIn("compiler.version=8", output)
        self.assertIn("compiler=clang", output)
        self.assertIn("arch=x86_64", output)
        self.assertIn("Cross-build from 'Linux:x86_64' to 'Android:x86_64'", output)

    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    def test_docker_custom_pip_command(self):
        conanfile = textwrap.dedent("""
                from conans import ConanFile
                import os

                class Pkg(ConanFile):
                    settings = "os", "compiler", "build_type", "arch"
                    requires = "zlib/1.2.11"

                    def build(self):
                        pass
            """)
        self.save_conanfile(conanfile)
        with tools.environment_append({"CONAN_DOCKER_ENTRY_SCRIPT": "pip install -U /tmp/cpt",
                                       "CONAN_USERNAME": "bar",
                                       "CONAN_DOCKER_IMAGE": "conanio/gcc8",
                                       "CONAN_REFERENCE": "foo/0.0.1@bar/testing",
                                       "CONAN_DOCKER_RUN_OPTIONS": "--network=host, --add-host=host.docker.internal:host-gateway,--add-host=google.com:8.8.8.8 -v{}:/tmp/cpt".format(
                                           self.root_project_folder),
                                       "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                                       "CONAN_FORCE_SELINUX": "TRUE",
                                       "CONAN_DOCKER_SHELL": "/bin/bash -c",
                                       "CONAN_DOCKER_PIP_COMMAND": "foobar"
                                       }):
            self.packager = ConanMultiPackager(gcc_versions=["8"],
                                               archs=["x86_64"],
                                               build_types=["Release"],
                                               out=self.output.write)
            self.packager.add({})
            with self.assertRaises(Exception) as raised:
                self.packager.run()
                self.assertIn("Error updating the image", str(raised.exception))
                self.assertIn("foobar install conan_package_tools", str(raised.exception))

    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    @unittest.skipIf(is_github_actions(), "FIXME: It fails on Github Actions")
    def test_docker_base_profile(self):
        conanfile = textwrap.dedent("""
                from conans import ConanFile

                class Pkg(ConanFile):

                    def build(self):
                        pass
            """)

        self.save_conanfile(conanfile)
        with tools.environment_append({"CONAN_DOCKER_RUN_OPTIONS": "--network=host -v{}:/tmp/cpt".format(self.root_project_folder),
                                       "CONAN_DOCKER_ENTRY_SCRIPT": "pip install -U /tmp/cpt",
                                       "CONAN_DOCKER_IMAGE": "conanio/gcc8",
                                       "CONAN_USE_DOCKER": "1",
                                       "CONAN_REFERENCE": "foo/0.0.1@bar/testing",
                                       "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                                       "CONAN_FORCE_SELINUX": "TRUE",
                                       "CONAN_DOCKER_USE_SUDO": "FALSE",
                                       "CONAN_DOCKER_SHELL": "/bin/bash -c",
                                       }):
            self.packager = ConanMultiPackager(gcc_versions=["8"],
                                               archs=["x86_64"],
                                               build_types=["Release"],
                                               config_url="https://github.com/bincrafters/bincrafters-config.git",
                                               out=self.output.write)
            self.packager.add({})
            self.packager.run(base_profile_name="linux-gcc8-amd64")
            self.assertIn('Using specified default base profile: linux-gcc8-amd64', self.output)
            self.assertIn('-e CPT_BASE_PROFILE_NAME="linux-gcc8-amd64"', self.output)

    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    @unittest.skipIf(is_github_actions(), "FIXME: It fails on Github Actions")
    def test_docker_base_build_profile(self):
        conanfile = textwrap.dedent("""
                    from conans import ConanFile

                    class Pkg(ConanFile):

                        def build(self):
                            pass
                """)

        self.save_conanfile(conanfile)
        with tools.environment_append(
                {"CONAN_DOCKER_RUN_OPTIONS": "--network=host -v{}:/tmp/cpt".format(self.root_project_folder),
                 "CONAN_DOCKER_ENTRY_SCRIPT": "pip install -U /tmp/cpt",
                 "CONAN_DOCKER_IMAGE": "conanio/gcc8",
                 "CONAN_USE_DOCKER": "1",
                 "CONAN_REFERENCE": "foo/0.0.1@bar/testing",
                 "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                 "CONAN_FORCE_SELINUX": "TRUE",
                 "CONAN_DOCKER_USE_SUDO": "FALSE",
                 "CONAN_DOCKER_SHELL": "/bin/bash -c",
                 }):
            self.packager = ConanMultiPackager(gcc_versions=["8"],
                                               archs=["x86_64"],
                                               build_types=["Release"],
                                               config_url="https://github.com/bincrafters/bincrafters-config.git",
                                               out=self.output.write)
            self.packager.add({})
            self.packager.run(base_profile_name="orangepi", base_profile_build_name="linux-gcc8-amd64")
            self.assertIn('Using specified default base profile: orangepi', self.output)
            self.assertIn('Using specified build profile: linux-gcc8-amd64', self.output)
            self.assertIn('-e CPT_BASE_PROFILE_NAME="orangepi"', self.output)
            self.assertNotIn('-e CPT_PROFILE_BUILD="linux-gcc8-amd64"', self.output)


    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    def test_docker_hidden_password(self):
        conanfile = textwrap.dedent("""
                from conans import ConanFile

                class Pkg(ConanFile):
                    settings = "os", "compiler", "build_type", "arch"

                    def build(self):
                        pass
            """)

        self.save_conanfile(conanfile)
        with tools.environment_append({"CONAN_USERNAME": "bar",
                                       "CONAN_LOGIN_USERNAME": "foobar",
                                       "CONAN_PASSWORD": "foobazcouse",
                                       "CONAN_DOCKER_IMAGE": "conanio/gcc8",
                                       "CONAN_REFERENCE": "foo/0.0.1@bar/testing",
                                       "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                                       "CONAN_FORCE_SELINUX": "TRUE",
                                       "CONAN_DOCKER_USE_SUDO": "FALSE",
                                       "CONAN_DOCKER_SHELL": "/bin/bash -c",
                                       }):
            self.packager = ConanMultiPackager(gcc_versions=["8"],
                                               archs=["x86_64"],
                                               build_types=["Release"],
                                               out=self.output.write)
            self.packager.add({})
            self.packager.run()
            self.assertIn('-e CONAN_LOGIN_USERNAME="xxxxxxxx"', self.output)
            self.assertIn('-e CONAN_PASSWORD="xxxxxxxx"', self.output)

    @unittest.skipUnless(is_linux_and_have_docker(), "Requires Linux and Docker")
    def test_docker_underscore_user_channel(self):
        conanfile = textwrap.dedent("""
                from conans import ConanFile

                class Pkg(ConanFile):
                    def build(self):
                        pass
            """)

        self.save_conanfile(conanfile)
        with tools.environment_append({"CONAN_USERNAME": "_",
                                       "CONAN_CHANNEL": "_",
                                       "CONAN_DOCKER_IMAGE": "conanio/gcc8",
                                       "CONAN_REFERENCE": "foo/0.0.1",
                                       "CONAN_DOCKER_IMAGE_SKIP_UPDATE": "TRUE",
                                       "CONAN_FORCE_SELINUX": "TRUE",
                                       "CONAN_DOCKER_USE_SUDO": "FALSE",
                                       "CONAN_DOCKER_SHELL": "/bin/bash -c",
                                       }):
            self.packager = ConanMultiPackager(gcc_versions=["8"],
                                               archs=["x86_64"],
                                               build_types=["Release"],
                                               out=self.output.write)
            self.packager.add({})
            self.packager.run()
            self.assertIn('-e CONAN_USERNAME="_"', self.output)
            self.assertIn('-e CONAN_CHANNEL="_"', self.output)
