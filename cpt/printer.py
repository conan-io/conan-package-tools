import sys
from tabulate import tabulate
from contextlib import contextmanager
from cpt import __version__ as version


class Printer(object):

    def __init__(self, printer=None):
        self.printer = printer or sys.stdout.write

    def print_in_docker(self, container=None):
        text = """
                    ##        .
              ## ## ##       ==
           ## ## ## ##      ===
       /*********************\___/ ===
  ~~~ {~~ ~~~~ ~~~ ~~~~ ~~ ~ /  ===- ~~~
       \______ o          __/
         \    \        __/
          \____\______/

       You are in Docker now! %s
""" % container or ""
        self.printer(text)

    def print_ascci_art(self):
        text = """
       _____                          _____           _                      _______          _
      / ____|                        |  __ \         | |                    |__   __|        | |
     | |     ___  _ __   __ _ _ __   | |__) |_ _  ___| | ____ _  __ _  ___     | | ___   ___ | |___
     | |    / _ \| '_ \ / _` | '_ \  |  ___/ _` |/ __| |/ / _` |/ _` |/ _ \    | |/ _ \ / _ \| / __|
     | |___| (_) | | | | (_| | | | | | |  | (_| | (__|   < (_| | (_| |  __/    | | (_) | (_) | \__ \\
      \_____\___/|_| |_|\__,_|_| |_| |_|   \__,_|\___|_|\_\__,_|\__, |\___|    |_|\___/ \___/|_|___/
                                                                 __/ |
                                                                |___/

    """
        self.printer(text)
        self.printer("\nVersion: %s" % version)

    @contextmanager
    def foldable_output(self, name):
        self.start_fold(name)
        yield
        sys.stderr.flush()
        sys.stdout.flush()
        self.end_fold(name)
        sys.stdout.flush()

    ACTIVE_FOLDING = False  # Not working ok because process output in wrong order

    def start_fold(self, name):
        from cpt.ci_manager import is_travis
        if self.ACTIVE_FOLDING and is_travis():
            self.printer("\ntravis_fold:start:%s\n" % name)
        else:
            self.printer("\n[%s]\n" % name)

    def end_fold(self, name):
        from cpt.ci_manager import is_travis
        if self.ACTIVE_FOLDING and is_travis():
            self.printer("\ntravis_fold:end:%s\n" % name)

    def print_command(self, command):
        self.print_rule(char="_")
        self.printer("\n >> %s\n" % command)
        self.print_rule(char="_")

    def print_message(self, title, body=""):
        self.printer("\n >> %s\n" % title)
        if body:
            self.printer("   >> %s\n" % body)

    def print_profile(self, text):
        self.printer(tabulate([[text, ]], headers=["Profile"], tablefmt='psql'))
        self.printer("\n")

    def print_rule(self, char="*"):
        self.printer("\n")
        self.printer(char * 100)
        self.printer("\n")

    def print_current_page(self, current_page, total_pages):
        self.printer("Page: %s/%s" % (current_page, total_pages))
        self.printer("\n")

    def print_dict(self, data):
        table = [("Configuration", "value")]
        for name, value in data.items():
            table.append((name, value))
        self.printer(tabulate(table, headers="firstrow", tablefmt='psql'))
        self.printer("\n")

    def print_jobs(self, all_jobs):
        compiler_headers_ext = set()
        option_headers = set()
        for build in all_jobs:
            compiler_headers_ext.update(build.settings.keys())
            option_headers.update(build.options.keys())

        compiler_headers = [it for it in compiler_headers_ext]

        table = []
        for i, build in enumerate(all_jobs):
            table.append([build.settings.get(it, "") for it in compiler_headers] +
                         [build.options.get(it, '') for it in option_headers])

        if len(table):
            self.printer(tabulate(table, headers=list(compiler_headers) + list(option_headers),
                             # showindex=True,
                             tablefmt='psql'))
            self.printer("\n")
        else:
            self.printer("There are no jobs!\n")
        self.printer("\n")
