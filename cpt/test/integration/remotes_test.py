from cpt.printer import Printer
from cpt.remotes import RemotesManager
from cpt.test.integration.base import BaseTest


class RemotesTest(BaseTest):

    def test_duplicated_remotes_with_different_url(self):

        self.api.remote_remove("conancenter")
        self.api.remote_add("upload_repo", "url_different", True)

        manager = RemotesManager(self.api, Printer(), remotes_input="url1@True@upload_repo",
                                 upload_input="url1@True@upload_repo")

        remotes = self.api.remote_list()
        self.assertIsNotNone(manager._get_remote_by_name(remotes, "upload_repo"))

        manager.add_remotes_to_conan()

        self.assertEquals(len(self.api.remote_list()), 1)

        manager.add_remotes_to_conan()

        self.assertEquals(len(self.api.remote_list()), 1)

    def test_duplicated_remotes_with_same_url(self):

        self.api.remote_remove("conancenter")
        self.api.remote_add("upload_repo", "url1", True)

        manager = RemotesManager(self.api, Printer(), remotes_input="url1@True@upload_repo",
                                 upload_input="url1@True@upload_repo")

        remotes = self.api.remote_list()
        self.assertIsNotNone(manager._get_remote_by_name(remotes, "upload_repo"))

        manager.add_remotes_to_conan()
        self.assertEquals(len(self.api.remote_list()), 1)
