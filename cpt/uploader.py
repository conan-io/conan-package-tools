from cpt.printer import print_message


class Uploader(object):

    def __init__(self, remote_name):
        self._remote_name = remote_name


def upload_packages(reference, remote_name):

    self.login("upload_repo")

    all_refs = set([ref for _, _, _, _, ref in self.builds_in_current_page])

    if not all_refs:
        all_refs = [reference]

    if not all_refs:
        print_message("NOT REFERENCES TO UPLOAD!!")

    for ref in all_refs:
        command = "conan upload %s --retry %s --all --force --confirm -r=upload_repo" % (
                str(ref), self.upload_retry)

        print_message("RUNNING UPLOAD COMMAND", "$ %s" % command)
        ret = self.runner(command)
        if ret != 0:
            raise Exception("Error uploading")


