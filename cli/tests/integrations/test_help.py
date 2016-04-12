from .common import assert_command


def test_help():
    with open('tests/data/help/help.txt') as content:
        assert_command(['dcos', 'help', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    assert_command(['dcos', 'help', '--info'],
                   stdout=b'Display help information about DCOS\n')


def test_version():
    assert_command(['dcos', 'help', '--version'],
                   stdout=b'dcos-help version SNAPSHOT\n')


def test_list():
    stdout = """\
Command line utility for the Mesosphere Datacenter Operating
System (DCOS). The Mesosphere DCOS is a distributed operating
system built around Apache Mesos. This utility provides tools
for easy management of a DCOS installation.

Available DCOS commands:

\tauth           \tAuthenticate to DCOS cluster
\tconfig         \tManage the DCOS configuration file
\thelp           \tDisplay help information about DCOS
\tmarathon       \tDeploy and manage applications to DCOS
\tnode           \tAdminister and manage DCOS cluster nodes
\tpackage        \tInstall and manage DCOS software packages
\tservice        \tManage DCOS services
\ttask           \tManage DCOS tasks

Get detailed command description with 'dcos <command> --help'.
""".encode('utf-8')

    assert_command(['dcos', 'help'],
                   stdout=stdout)


def test_help_config():
    with open('tests/data/help/config.txt') as content:
        assert_command(['dcos', 'help', 'config'],
                       stdout=content.read().encode('utf-8'))


def test_help_marathon():
    with open('tests/data/help/marathon.txt') as content:
        assert_command(['dcos', 'help', 'marathon'],
                       stdout=content.read().encode('utf-8'))


def test_help_node():
    with open('tests/data/help/node.txt') as content:
        assert_command(['dcos', 'help', 'node'],
                       stdout=content.read().encode('utf-8'))


def test_help_package():
    with open('tests/data/help/package.txt') as content:
        assert_command(['dcos', 'help', 'package'],
                       stdout=content.read().encode('utf-8'))


def test_help_service():
    with open('tests/data/help/service.txt') as content:
        assert_command(['dcos', 'help', 'service'],
                       stdout=content.read().encode('utf-8'))


def test_help_task():
    with open('tests/data/help/task.txt') as content:
        assert_command(['dcos', 'help', 'task'],
                       stdout=content.read().encode('utf-8'))


def test_help_auth():
    with open('tests/data/help/auth.txt') as content:
        assert_command(['dcos', 'help', 'auth'],
                       stdout=content.read().encode('utf-8'))
