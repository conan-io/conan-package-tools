
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
