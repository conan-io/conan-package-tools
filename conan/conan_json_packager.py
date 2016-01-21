from conan.packager import ConanMultiPackager
import os


def run():
    """Reads environment json to create a ConanMultiPackager,
    It can run packages with pagination with
    CONAN_TOTAL_PAGES and CONAN_CURRENT_PAGE"""
    the_json = os.getenv("CONAN_BUILDER_ENCODED", None)
    current_page = int(os.getenv("CONAN_CURRENT_PAGE", "1"))
    total_pages = int(os.getenv("CONAN_TOTAL_PAGES", "1"))

    builder = ConanMultiPackager.deserialize(the_json)
    builder.pack(current_page, total_pages)

if __name__ == '__main__':
    run()
