from conans.client.remote_registry import Remote
from cpt.printer import Printer
from cpt.remotes import RemotesManager
from cpt.test.integration.base import BaseTest


class RemotesTest(BaseTest):

    def test_duplicated_remotes_with_different_url(self):

        self.api.remote_remove("conan-center")
        self.api.remote_add("upload_repo", "url_different", True)

        manager = RemotesManager(self.api, Printer(), remotes_input="url1@True@upload_repo",
                                 upload_input="url1@True@upload_repo")

        remotes = self.api.remote_list()
        self.assertIsNotNone(manager._get_remote_by_name(remotes, "upload_repo"))

        expected_remote = [Remote(name='upload_repo', url='url_different', verify_ssl=True)]
        self.assertEqual(expected_remote, remotes)

        manager.add_remotes_to_conan()

        remotes = self.api.remote_list()
        self.assertEquals(len(self.api.remote_list()), 1)

        expected_remote = [Remote(name='upload_repo', url='url1', verify_ssl=True)]
        self.assertEqual(expected_remote, remotes)

        manager.add_remotes_to_conan()

        self.assertEquals(len(self.api.remote_list()), 1)
        self.assertEqual(expected_remote, remotes)

    def test_duplicated_remotes_with_same_url(self):

        self.api.remote_remove("conan-center")
        self.api.remote_add("upload_repo", "url1", True)

        manager = RemotesManager(self.api, Printer(), remotes_input="url1@True@upload_repo",
                                 upload_input="url1@True@upload_repo")

        remotes = self.api.remote_list()
        self.assertIsNotNone(manager._get_remote_by_name(remotes, "upload_repo"))

        expected_remote = [Remote(name='upload_repo', url='url1', verify_ssl=True)]
        self.assertEqual(expected_remote, remotes)

        manager.add_remotes_to_conan()
        self.assertEquals(len(self.api.remote_list()), 1)
        self.assertEqual(expected_remote, remotes)
