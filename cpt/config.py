import os.path
from conans import tools
from conans.model.conf import ConfDefinition


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
        config = ConfDefinition()
        if os.path.exists(global_conf):
            content = tools.load(global_conf)
            config.loads(content)
        for value in values:
            key = value[:value.find('=')]
            k_value = value[value.find('=') + 1:]
            config.update(key, k_value)
        tools.save(global_conf, config.dumps())
