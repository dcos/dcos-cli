from .common import assert_command, exec_command


def test_default():
    returncode, stdout, stderr = exec_command(['dcos'])

    assert returncode == 0
    assert stdout == """\
Command line utility for the Mesosphere Datacenter Operating
System (DCOS). The Mesosphere DCOS is a distributed operating
system built around Apache Mesos. This utility provides tools
for easy management of a DCOS installation.

Available DCOS commands:

\tconfig         \tGet and set DCOS CLI configuration properties
\thelp           \tDisplay command line usage information
\tmarathon       \tDeploy and manage applications on the DCOS
\tnode           \tManage DCOS nodes
\tpackage        \tInstall and manage DCOS packages
\tservice        \tManage DCOS services
\ttask           \tManage DCOS tasks

Get detailed command description with 'dcos <command> --help'.
""".encode('utf-8')
    assert stderr == b''


def test_help():
    stdout = b"""\
Command line utility for the Mesosphere Datacenter Operating
System (DCOS)

'dcos help' lists all available subcommands. See 'dcos <command> --help'
to read about a specific subcommand.

Usage:
    dcos [options] [<command>] [<args>...]

Options:
    --help                      Show this screen
    --version                   Show version
    --log-level=<log-level>     If set then print supplementary messages to
                                stderr at or above this level. The severity
                                levels in the order of severity are: debug,
                                info, warning, error, and critical. E.g.
                                Setting the option to warning will print
                                warning, error and critical messages to stderr.
                                Note: that this does not affect the output sent
                                to stdout by the command.
    --debug                     If set then enable further debug messages which
                                are sent to stdout.

Environment Variables:
    DCOS_LOG_LEVEL              If set then it specifies that message should be
                                printed to stderr at or above this level. See
                                the --log-level option for details.

    DCOS_CONFIG                 This environment variable points to the
                                location of the DCOS configuration file.
                                [default: ~/.dcos/dcos.toml]

    DCOS_DEBUG                  If set then enable further debug messages which
                                are sent to stdout.
"""

    assert_command(['dcos', '--help'],
                   stdout=stdout)


def test_version():
    assert_command(['dcos', '--version'],
                   stdout=b'dcos version SNAPSHOT\n')


def test_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=info', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS CLI configuration properties\n"


def test_capital_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=INFO', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS CLI configuration properties\n"


def test_invalid_log_level_flag():
    stdout = (b"Log level set to an unknown value 'blah'. Valid "
              b"values are ['debug', 'info', 'warning', 'error', "
              b"'critical']\n")

    assert_command(
        ['dcos', '--log-level=blah', 'config', '--info'],
        returncode=1,
        stdout=stdout)
