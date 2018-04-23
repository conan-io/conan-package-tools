import os
import sys
import tempfile
from collections import namedtuple

from conans import tools
from conans.client.profile_loader import _load_profile
from conans.util.files import save
from cpt import __version__ as package_tools_version
from cpt.printer import Printer


class TestPackageRunner(object):

    def __init__(self, profile_text, reference, conan_api, uploader,
                 args=None, conan_pip_package=None, exclude_vcvars_precommand=False,
                 build_policy=None, runner=None, abs_folder=None, printer=None):

        self.printer = printer or Printer()
        self._abs_folder = abs_folder or os.getcwd()
        self._uploader = uploader
        self._conan_api = conan_api
        self._client_cache = self._conan_api._client_cache
        self._profile_text = profile_text
        self._reference = reference
        self._args = args
        self._conan_pip_package = conan_pip_package
        self._exclude_vcvars_precommand = exclude_vcvars_precommand
        self._build_policy = build_policy
        self._runner = PrintRunner(runner or os.system, self.printer)

        if "default" in self._profile_text:  # User didn't specified a custom profile
            default_profile_name = os.path.basename(self._client_cache.default_profile_path)
            if not os.path.exists(self._client_cache.default_profile_path):
                self._conan_api.create_profile(default_profile_name, detect=True)

            if default_profile_name != "default":  # User have a different default profile name
                # https://github.com/conan-io/conan-package-tools/issues/121
                self._profile_text = self._profile_text.replace("include(default)",
                                                                "include(%s)" % default_profile_name)

        # Save the profile in a tmp file
        tmp = os.path.join(tempfile.mkdtemp(suffix='conan_package_tools_profiles'), "profile")
        self._abs_profile_path = os.path.abspath(tmp)
        save(self._abs_profile_path, self._profile_text)

        self._profile, _ = _load_profile(self._profile_text,
                                         os.path.dirname(self._abs_profile_path),
                                         self._client_cache.profiles_path)

        self._uploader.remote_manager.add_remotes_to_conan()

    @property
    def settings(self):
        return self._profile.settings

    @property
    def options(self):
        return self._profile.options

    def run(self):
        context = tools.no_op()
        compiler = self.settings.get("compiler", None)
        if not self._exclude_vcvars_precommand:
            if compiler == "Visual Studio" and "compiler.version" in self.settings:
                compiler_set = namedtuple("compiler", "version")(self.settings["compiler.version"])
                mock_sets = namedtuple("mock_settings",
                                       "arch compiler get_safe")(self.settings["arch"], compiler_set,
                                                                 lambda x: self.settings.get(x, None))
                context = tools.vcvars(mock_sets)
        with context:
            self.printer.print_rule()
            self.printer.print_profile(self._profile_text)

            with self.printer.foldable_output("conan_create"):
                # TODO: Get uploaded packages with Conan 1.3 from the ret json
                self.printer.print_message("Calling 'conan create'")
                name, version, user, channel = self._reference
                self._conan_api.create(self._abs_folder, name=name, version=version, user=user, channel=channel,
                                       build_modes=self._build_policy,
                                       profile_name=self._abs_profile_path)

                self._uploader.upload_packages(self._reference)


class DockerTestPackageRunner(TestPackageRunner):
    def __init__(self, profile_text, reference, conan_api, uploader, runner=None,
                 args=None, conan_pip_package=None, docker_image=None, sudo_docker_command=True,
                 docker_image_skip_update=False, build_policy=None,
                 always_update_conan_in_docker=False):

        super(DockerTestPackageRunner, self).__init__(profile_text, reference, conan_api, uploader,
                                                      args=args, conan_pip_package=conan_pip_package,
                                                      build_policy=build_policy, runner=runner)

        self._docker_image = docker_image
        self._always_update_conan_in_docker = always_update_conan_in_docker
        self._docker_image_skip_update = docker_image_skip_update
        self._sudo_docker_command = sudo_docker_command

    def pip_update_conan_command(self):
        command = "sudo pip install conan_package_tools==%s --upgrade" % package_tools_version
        if self._conan_pip_package:
            command += " && sudo pip install %s" % self._conan_pip_package
        else:
            command += " && sudo pip install conan --upgrade"

        return command

    def run(self, pull_image=True, docker_entry_script=None):
        if pull_image:
            self.pull_image()
            if not self._docker_image_skip_update and not self._always_update_conan_in_docker:
                # Update the downloaded image
                with self.printer.foldable_output("update conan"):
                    command = '%s docker run --name ' \
                              'conan_runner %s /bin/sh -c "%s"' % (self._sudo_docker_command,
                                                                   self._docker_image,
                                                                   self.pip_update_conan_command())
                    self._runner(command)
                    # Save the image with the updated installed
                    # packages and remove the intermediate container
                    command = "%s docker commit conan_runner %s" % (self._sudo_docker_command,
                                                                    self._docker_image)
                    self._runner(command)

                    command = "%s docker rm conan_runner" % self._sudo_docker_command
                    self._runner(command)

        # Run the build
        envs = self.get_env_vars()
        env_vars_text = " " + " ".join(['-e %s="%s"' % (key, value)
                                        for key, value in envs.items() if value])

        if self._always_update_conan_in_docker:
            update_command = self.pip_update_conan_command() + " && "
        else:
            update_command = ""
        command = ("%s docker run --rm -v %s:/home/conan/project %s %s /bin/sh "
                   "-c \" cd project && "
                   "%s run_create_in_docker \"" % (self._sudo_docker_command, os.getcwd(),
                                                   env_vars_text, self._docker_image,
                                                   update_command))

        # Push entry command before to build
        if docker_entry_script:
            command = command.replace("run_create_in_docker",
                                      "%s && run_create_in_docker" % docker_entry_script)

        ret = self._runner(command)
        if ret != 0:
            raise Exception("Error building: %s" % command)

    def pull_image(self):
        with self.printer.foldable_output("docker pull"):
            self._runner("%s docker pull %s" % (self._sudo_docker_command, self._docker_image))

    def get_env_vars(self):
        ret = {key: value for key, value in os.environ.items() if key.startswith("CONAN_")}
        ret["CPT_ARGS"] = escape_env(self._args)
        ret["CONAN_REFERENCE"] = self._reference
        ret["CPT_PROFILE"] = escape_env(self._profile_text)
        ret["CPT_PIP_PACKAGE"] = escape_env(self._conan_pip_package)
        ret["CPT_BUILD_POLICY"] = escape_env(self._build_policy)

        return ret


def unscape_env(text):
    if not text:
        return text
    return text.replace("@@", "\n").replace('||', '"')


def escape_env(text):
    if not text:
        return text
    return text.replace("\n", "@@").replace('"', '||')


class PrintRunner(object):

    def __init__(self, runner, printer):
        self.runner = runner
        self.printer = printer

    def __call__(self, command):
        self.printer.print_command(command)
        sys.stderr.flush()
        sys.stdout.flush()
        return self.runner(command)
