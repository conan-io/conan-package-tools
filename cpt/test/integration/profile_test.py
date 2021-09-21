import os
import textwrap

from conans import tools

from cpt.test.integration.base import BaseTest
from cpt.packager import ConanMultiPackager


class ProfileTest(BaseTest):

    def test_build_context_support(self):
        conanfile = textwrap.dedent("""
                from conans import ConanFile
                class Pkg(ConanFile):
                    pass
                """)
        self.save_conanfile(conanfile)
        build_profile = textwrap.dedent("""
                [settings]
                os=Linux
                arch=x86_64
                compiler=gcc
                compiler.version=8
                compiler.libcxx=libstdc++
                build_type=Release
                [options]
                [build_requires]
                [env]
                [conf]
                """)
        build_profile_path = os.path.join(self.tmp_folder, "build_profile")
        tools.save(build_profile_path, build_profile)

        host_profile = textwrap.dedent("""
                        [settings]
                        arch=armv7hf
                        build_type=Release
                        [options]
                        [build_requires]
                        [env]
                        [conf]
                        """)
        host_profile_path = os.path.join(self.tmp_folder, "host_profile")
        tools.save(host_profile_path, host_profile)
        self.packager = ConanMultiPackager(username="elcidcampeador",
                                           reference="tizona/1.0.40@elcidcampeador/testing", out=self.output.write)
        self.packager.add_common_builds()
        self.packager.run_builds(curpage=1, total_pages=1, base_profile_name=host_profile_path,
                                 base_profile_build_name=build_profile_path)
        self.assertIn("Using specified default base profile", self.output)
        self.assertIn("Using specified build profile", self.output)
