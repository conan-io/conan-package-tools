import os.path
from conans import tools


class ConfigManager(object):

    def __init__(self, conan_api, printer):
        self._conan_api = conan_api
        self.printer = printer

    def install(self, url, args=None):
        message = "Installing config from address %s" % url
        if args:
            message += " with args \"%s\"" % args
        self.printer.print_message(message)
        self._conan_api.config_install(url, verify_ssl=True, args=args)


class GlobalConf(object):
    def __init__(self, conan_api, printer):
        self._conan_api = conan_api
        self.printer = printer

    def populate(self, values):
        global_conf = self._conan_api.app.cache.new_config_path
        if isinstance(values, str):
            values = values.split(",")
        if os.path.exists(global_conf) and os.path.isfile(global_conf):
            content = tools.load(global_conf)
            content += "\n" + values.join("\n")
            tools.save(global_conf, content)
        else:
            tools.save(global_conf, values.join("\n"))
