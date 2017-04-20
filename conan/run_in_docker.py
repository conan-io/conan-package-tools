import os
from conan.log import logger

from conan.test_package_runner import DockerTestPackageRunner


def run():
    the_json = os.getenv("CONAN_RUNNER_ENCODED", None)
    runner = DockerTestPackageRunner.deserialize(the_json)
    logger.info("Running test_package in a Docker image: %s" % the_json)
    runner.run()

if __name__ == '__main__':
    run()
