import os
import platform
from conan.log import logger

DEFAULT_NPAKCD_INSTALLER = "http://bit.ly/npackdcl-1_21_6"
DEFAULT_NPACKD_INSTALL_PREFIX = "C:\\Program Files (x86)\\NpackdCL"


class NPackdHelper(object):

    def __init__(self):
        self.npackd_installer = os.getenv("NPAKCD_INSTALLER", DEFAULT_NPAKCD_INSTALLER)
        self.npackd_install_path = os.getenv("NPACKD_INSTALL_PREFIX", DEFAULT_NPACKD_INSTALL_PREFIX)

    @property
    def npackd_exe(self):
        return os.path.join(self.npackd_install_path, "ncl.exe")

    def install(self):
        ret = os.system('msiexec.exe /qn /i "%s"' % self.npackd_installer)
        print(ret)
        if ret != 0:
            raise Exception("Failed install npackd")

        command = '""%s" set-repo -u https://npackd.appspot.com/rep/xml?tag=stable -u https://npackd.appspot.com/rep/xml?tag=stable64"' % self.npackd_exe
        print(command)
        ret = os.system(command)
        if ret != 0:
            raise Exception("Failed adding npackd repository")

        ret = os.system('""%s" detect"' % self.npackd_exe)
        if ret != 0:
            raise Exception("Failed detecting npackd")


class MinGWHelper(object):

    def __init__(self, configurations=None, pure_c=False):
        '''configurations is a list of tuples:
        [(version, arch, exception, thread), (version, arch, exception, thread)]

        arch => ["x86", "x86_64"]
        exception => ["dwarf2", "sjlj", "seh"]
        thread => ["posix", "win"]
        '''
        if platform.system() != "Windows":
            raise "Only for windows!"
        # mingw-w64-i686-dw2-posix
        # mingw-w64-i686-dw2-win
        # mingw-w64-i686-sjlj-posix
        # mingw-w64-i686-sjlj-win

        # mingw-w64-x86_64-seh-posix
        # mingw-w64-x86_64-seh-win
        # mingw-w64-x86_64-sjlj-posix
        # mingw-w64-x86_64-sjlj-win

        self.configurations = configurations or []
        self.install_path = os.getenv("CONAN_MINGW_INSTALL_PATH", os.path.expanduser(os.path.join("~", ".conan")))
        self.logger = logger
        self.pure_c = pure_c

        for config in self.configurations:
            version, arch, exception, thread = config
            if (arch == "x86" and exception == "seh") or \
               (arch == "x86_64" and exception == "dwarf2"):
                self.logger.error("Skipped invalid configuration: %s" % config)
                return
            if thread not in ["posix", "win32"]:
                self.logger.error("Invalid thread setting: %s" % thread)
                return
            if exception not in ["seh", "sjlj", "dwarf2"]:
                self.logger.error("Invalid thread setting: %s" % exception)
                return
            if version[0:3] not in ["4.8", "4.9"]:
                self.logger.error("Invalid version setting: %s" % (version))
                return

    def compiler_path(self, arch, exception, thread):
        return os.path.join(self.install_path,
                            self.package_name(arch, exception, thread))

    @staticmethod
    def package_name(arch, exception, thread):
        arch_name = {"x86": "i686", "i686": "i686"}.get(arch, "x86_64")
        exception = {"dwarf2": "dw2"}.get(exception, exception)
        name = "mingw-w64-%s-%s-%s" % (arch_name, exception, thread)
        return name

    def install_all(self):
        for config in self.configurations:
            self.install(*config)

    def install(self, version, arch, exception, thread):
        npackd = NPackdHelper()
        if not os.path.exists('%s' % npackd.npackd_exe):
            npackd.install()
        p_name = self.package_name(arch, exception, thread)
        version = {"4.9": "4.9.2",
                   "4.9.2": "4.9.2",
                   "4.8": "4.8.2",
                   "4.8.2": "4.8.2"}.get(version)
        command = '""%s" add -p %s -v %s -f %s/%s"' % (npackd.npackd_exe, p_name, version,
                                                       self.install_path, p_name)
        self.logger.debug("Installing MinGW %s %s %s %s" % (version, arch, exception, thread))
        ret = os.system(command)
        if ret != 0:
            raise Exception(command)

        return self.compiler_path(arch, exception, thread)

    def generate_builds(self):
        builds = []
        for config in self.configurations:
            version, arch, exception, thread = config
            settings = {"arch": arch, "compiler": "gcc",
                        "compiler.version": version[0:3],
                        "compiler.threads": thread,
                        "compiler.exception": exception}
            if self.pure_c:
                settings.update({"compiler.libcxx": "libstdc++"})
            settings.update({"build_type": "Release"})
            builds.append((settings, {}))
            settings.update({"build_type": "Debug"})
            builds.append((settings, {}))
        return builds


if __name__ == "__main__":
    from conan.packager import ConanMultiPackager
#     mp = ConanMultiPackager()
#     print(mp.conan_compiler_info())
    mingw = MinGWHelper(configurations=[("4.9", "x86_64", "seh", "posix"),
                                        ("4.9", "x86_64", "sjlj", "posix"),
                                        ("4.9", "x86", "sjlj", "posix"),
                                        ("4.9", "x86", "dwarf2", "posix")],
                        pure_c=True)
    builder = ConanMultiPackager(username="lasote")
    builder.builds.extend(mingw.generate_builds())
    builder.run()
