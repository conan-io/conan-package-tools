

class Uploader(object):

    def __init__(self, conan_api, remote_manager, auth_manager, printer, upload_retry):
        self.conan_api = conan_api
        self.remote_manager = remote_manager
        self.auth_manager = auth_manager
        self.printer = printer
        self._upload_retry = upload_retry
        if not self._upload_retry:
            self._upload_retry = 0

    def upload_packages(self, reference, upload):
        remote_name = self.remote_manager.upload_remote_name
        if not remote_name:
            self.printer.print_message("Upload skipped, not upload remote available")
            return
        if not self.auth_manager.credentials_ready(remote_name):
            self.printer.print_message("Upload skipped, credentials for remote '%s' not available" % remote_name)
            return

        if upload:
            self.printer.print_message("Uploading packages for '%s'" % str(reference))
            self.auth_manager.login(remote_name)
            self.conan_api.upload(str(reference),
                                  all_packages=True,
                                  remote=remote_name,
                                  force=True,
                                  retry=self._upload_retry)
