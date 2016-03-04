import unittest
from conan.packager import ConanMultiPackager


class MockRunner(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = []

    def __call__(self, command):
        self.calls.append(command)
        return 0

    def tests_for(self, numbers):
        """Check if executor has ran the builds that are expected.
        numbers are integers"""
        def line_for_number(number):
            return "conan test . -s compiler=\"os%(number)d\" -s os=\"os%(number)d\" "\
                "-o option%(number)d=\"value%(number)d\"" % {"number": number}

        found_numbers = []
        for call in self.calls:
            if call.startswith("conan export"):
                continue
            if call.startswith("conan test"):
                found = None
                for number in numbers:
                    if call.startswith(line_for_number(number)):
                        found = number
                        break
                if found is not None:
                    found_numbers.append(number)
                else:
                    return False
        return set(found_numbers) == set(numbers)


class AppTest(unittest.TestCase):

    def setUp(self):
        self.runner = MockRunner()
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner)

    def testSerialize(self):
        self.packager.add({"os": "Windows", "compiler": "Visual Studio"},
                          {"option1": "value1", "option2": "value2"})

        serial = self.packager.serialize()
        self.assertEquals(serial, '{"username": "lasote", "conan_pip_package": null, "args": "--build missing -r conan.io", '\
                          '"builds": [[{"os": "Windows", "compiler": "Visual Studio"}, '\
                          '{"option2": "value2", "option1": "value1"}]], "channel": "mychannel"}')

        mp = ConanMultiPackager.deserialize(serial, username="lasote")
        self.assertEqual(mp.conan_pip_package, None)

        self.packager.conan_pip_package = "conan==0.0.1rc7"
        serial = self.packager.serialize()
        mp = ConanMultiPackager.deserialize(serial, username="lasote")
        self.assertEqual(mp.conan_pip_package, "conan==0.0.1rc7")

    def _add_build(self, number):
        self.packager.add({"os": "os%d" % number, "compiler": "os%d" % number},
                          {"option%d" % number: "value%d" % number,
                           "option%d" % number: "value%d" % number})

    def testPages(self):
        for number in xrange(10):
            self._add_build(number)

        # 10 pages, 1 per build
        self.packager.pack(1, 10)
        self.assertTrue(self.runner.tests_for([0]))

        # 2 pages, 5 per build
        self.runner.reset()
        self.packager.pack(1, 2)
        self.assertTrue(self.runner.tests_for([0, 2, 4, 6, 8]))

        self.runner.reset()
        self.packager.pack(2, 2)
        self.assertTrue(self.runner.tests_for([1, 3, 5, 7, 9]))

        # 3 pages, 4 builds in page 1 and 3 in the rest of pages
        self.runner.reset()
        self.packager.pack(1, 3)
        self.assertTrue(self.runner.tests_for([0, 3, 6, 9]))

        self.runner.reset()
        self.packager.pack(2, 3)
        self.assertTrue(self.runner.tests_for([1, 4, 7]))

        self.runner.reset()
        self.packager.pack(3, 3)
        self.assertTrue(self.runner.tests_for([2, 5, 8]))

    def testDocker(self):
        self.packager.docker_pack(1, 2, ["4.3", "5.2"])
        self.assertIn("sudo docker pull lasote/conangcc43", self.runner.calls[0])
        self.assertIn("-e CONAN_CURRENT_PAGE=1 -e CONAN_TOTAL_PAGES=2 ", self.runner.calls[1])
        self.assertIn('-e CONAN_BUILDER_ENCODED=\'{"username": "lasote"', self.runner.calls[1])
        self.assertIn('-e CONAN_USERNAME=lasote -e CONAN_CHANNEL=mychannel', self.runner.calls[1])

