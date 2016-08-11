from .common import assert_command


def test_help():
    with open('tests/data/help/help.txt') as content:
        assert_command(['dcos', 'help', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    assert_command(['dcos', 'help', '--info'],
                   stdout=b'Display help information about DC/OS\n')


def test_version():
    assert_command(['dcos', 'help', '--version'],
                   stdout=b'dcos-help version SNAPSHOT\n')


def test_list():
    stdout = """\
Command line utility for the Mesosphere Datacenter Operating
System (DC/OS). The Mesosphere DC/OS is a distributed operating
system built around Apache Mesos. This utility provides tools
for easy management of a DC/OS installation.

Available DC/OS commands:

\tauth           \tAuthenticate to DC/OS cluster
\tconfig         \tManage the DC/OS configuration file
\thelp           \tDisplay help information about DC/OS
\tjob            \tDeploy and manage jobs in DC/OS
\tmarathon       \tDeploy and manage applications to DC/OS
\tnode           \tAdminister and manage DC/OS cluster nodes
\tpackage        \tInstall and manage DC/OS software packages
\tservice        \tManage DC/OS services
\ttask           \tManage DC/OS tasks

Get detailed command description with 'dcos <command> --help'.
""".encode('utf-8')

    assert_command(['dcos', 'help'],
                   stdout=stdout)


def test_help_config():
    with open('tests/data/help/config.txt') as content:
        assert_command(['dcos', 'help', 'config'],
                       stdout=content.read().encode('utf-8'))


def test_help_job():
    with open('tests/data/help/job.txt') as content:
        assert_command(['dcos', 'help', 'job'],
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
