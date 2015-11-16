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
    with open('tests/data/help/dcos.txt') as content:
        assert_command(['dcos', '--help'],
                       stdout=content.read().encode('utf-8'))


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
