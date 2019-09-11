import unittest
import subprocess

from cpt.tools import get_os_docker_image


class ToolsTest(unittest.TestCase):

    def test_get_os_docker_image(self):
        self.assertEqual("linux", get_os_docker_image("conanio/gcc8"))
        self.assertEqual(None, get_os_docker_image(None))
        with self.assertRaises(subprocess.CalledProcessError):
            get_os_docker_image("conanio/foobar")
