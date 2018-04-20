from cpt.printer import print_message


class Uploader(object):

    def __init__(self, conan_api, remote_manager, auth_manager):
        self.conan_api = conan_api
        self.remote_manager = remote_manager
        self.auth_manager = auth_manager

    def upload_packages(self, reference):
        remote_name = self.remote_manager.upload_remote_name
        if not remote_name:
            print_message("Upload skipped, not upload remote available")
            return

        print_message("Uploading packages for '%s'" % str(reference))
        self.auth_manager.login(remote_name)
        self.conan_api.upload(str(reference), all_packages=True, remote=remote_name)
