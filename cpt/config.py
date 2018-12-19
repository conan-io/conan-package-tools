
class ConfigManager(object):

    def __init__(self, conan_api, printer):
        self._conan_api = conan_api
        self.printer = printer

    def install(self, url):
        self.printer.print_message("Installing config from address %s" % url)
        self._conan_api.config_install(url, verify_ssl=True)
