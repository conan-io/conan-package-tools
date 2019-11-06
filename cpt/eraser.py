# -*- coding: utf-8 -*-

class Eraser(object):
    """ Helper to connect on remove and remove outdated packages
    """

    def __init__(self, conan_api, remote_manager, auth_manager, printer, remove):
        """ Initialize Eraser instance
        :param conan_api: Conan API instance
        :param remote_manager: Remote manager instance
        :param auth_manager: Authication manager to access the remote
        :param printer: CPT output
        :param remove: True if should remove outdated packages from remote. Otherwise, False.
        """
        self.conan_api = conan_api
        self.remote_manager = remote_manager
        self.auth_manager = auth_manager
        self.printer = printer
        self.remove = remove

    def remove_outdated_packages(self, reference):
        """ Remove outdated packages from remote
        :param reference: Package reference e.g. foo/0.1.0@user/channel
        """
        if not self.remote_manager or not self.remote_manager.upload_remote_name:
            self.printer.print_message("Remove outdated skipped, no remote available")
            return
        remote_name = self.remote_manager.upload_remote_name

        if not self.auth_manager or not self.auth_manager.credentials_ready(remote_name):
            self.printer.print_message("Remove outdated skipped, credentials for remote '%s' not available" % remote_name)
            return

        if self.remove:
            self.printer.print_message("Removing outdated packages for '%s'" % str(reference))
            self.auth_manager.login(remote_name)
            self.conan_api.remove(pattern=str(reference),
                                  force=True,
                                  remote_name=remote_name,
                                  outdated=True)
