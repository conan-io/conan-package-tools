import sys
from tabulate import tabulate
from contextlib import contextmanager

def print_ascci_art(printer=sys.stdout.write):
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
    printer(text)


@contextmanager
def foldable_output(name):
    start_fold(name)
    yield
    sys.stderr.flush()
    sys.stdout.flush()
    end_fold(name)
    sys.stdout.flush()

ACTIVE_FOLDING = False  # Not working ok because process output in wrong order


def start_fold(name, printer=sys.stdout.write):
    from conan.ci_manager import is_travis
    if ACTIVE_FOLDING and is_travis():
        printer("\ntravis_fold:start:%s\n" % name)
    else:
        printer("\n[%s]\n" % name)


def end_fold(name, printer=sys.stdout.write):
    from conan.ci_manager import is_travis
    if ACTIVE_FOLDING and is_travis():
        printer("\ntravis_fold:end:%s\n" % name)


def print_command(command, printer=sys.stdout.write):
    printer("\n >> %s\n" % command)


def print_message(title, body="", printer=sys.stdout.write):
    printer("\n >> %s\n" % title.upper())
    if body:
        printer("   >> %s\n" % body)


def print_profile(text, printer=sys.stdout.write):
    printer(tabulate([[text, ]], headers=["Profile"], tablefmt='psql'))
    printer("\n")


def print_rule(printer=sys.stdout.write, char="*"):
    printer("\n")
    printer(char * 100)
    printer("\n")


def print_current_page(current_page, total_pages, printer=sys.stdout.write):
    printer("Page: %s/%s" % (current_page, total_pages))
    printer("\n")


def print_dict(data, printer=sys.stdout.write):
    table = [("Configuration", "value")]
    for name, value in data.items():
        table.append((name, value))
    printer(tabulate(table, headers="firstrow", tablefmt='psql'))
    printer("\n")


def print_jobs(all_jobs, printer=sys.stdout.write):
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
        printer(tabulate(table, headers=list(compiler_headers) + list(option_headers),
                         # showindex=True,
                         tablefmt='psql'))
        printer("\n")
    else:
        sys.stdout.write("There are no jobs!\n")
    printer("\n")
