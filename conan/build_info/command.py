import argparse
import os
from conan.build_info.conan_build_info import BuildInfoManager


class Extender(argparse.Action):
    '''Allows to use the same flag several times in a command and creates a list with the values.
       For example:
           conan install MyPackage/1.2@user/channel -o qt:value -o mode:2 -s cucumber:true
           It creates:
           options = ['qt:value', 'mode:2']
           settings = ['cucumber:true']
    '''

    def __call__(self, parser, namespace, values, option_strings=None):  # @UnusedVariable
        # Need None here incase `argparse.SUPPRESS` was supplied for `dest`
        dest = getattr(namespace, self.dest, None)
        if(not hasattr(dest, 'extend') or dest == self.default):
            dest = []
            setattr(namespace, self.dest, dest)
            # if default isn't set to None, this method might be called
            # with the default as `values` for other arguments which
            # share this destination.
            parser.set_defaults(**{self.dest: None})

        try:
            dest.extend(values)
        except ValueError:
            dest.append(values)


def run():

    parser = argparse.ArgumentParser(description='Extract build-info from a specified '
                                                 'conan trace log and send it to an artifactory '
                                                 'instance')
    parser.add_argument('build_name', help='Build name, e.j: "my_jenkins_project"')
    parser.add_argument('build_number', help='Build number, e.j: 2')
    parser.add_argument('artifactory_url', help='Artifactory instance url e.j:'
                                                ' "http://localhost:8081/artifactory"')
    parser.add_argument('repo_name',  help='Artifactory repo conan name. e.j: dev-conan')
    parser.add_argument('user', help='Artifactory username')
    parser.add_argument('password', help='Artifactory password')
    parser.add_argument('trace_path', help='Path to the conan trace log file e.j: '
                                           '/tmp/conan_trace.log')

    parser.add_argument('--env', nargs=1, action=Extender, help='Capture env var as a build env var e.j: --env CONAN_HOME')

    args = parser.parse_args()

    if not os.path.exists(args.trace_path):
        print("Error, conan trace log not found! '%s'" % args.trace_path)
        exit(1)

    print("asasd")
    print(args.env)
    exit(1)

    manager = BuildInfoManager()
    info = manager.build(args.trace_path, args.build_name, args.build_number, args.env)
    manager.send(info, args.artifactory_url, args.repo_name, args.user, args.password)

if __name__ == "__main__":
    run()
