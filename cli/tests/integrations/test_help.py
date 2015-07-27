from .common import assert_command


def test_help():
    stdout = b"""Display command line usage information

Usage:
    dcos help --info
    dcos help

Options:
    --help     Show this screen
    --info     Show a short description of this subcommand
    --version  Show version
"""
    assert_command(['dcos', 'help', '--help'],
                   stdout=stdout)


def test_info():
    assert_command(['dcos', 'help', '--info'],
                   stdout=b'Display command line usage information\n')


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

\tconfig         \tGet and set DCOS CLI configuration properties
\thelp           \tDisplay command line usage information
\tmarathon       \tDeploy and manage applications on the DCOS
\tnode           \tManage DCOS nodes
\tpackage        \tInstall and manage DCOS packages
\tservice        \tManage DCOS services
\ttask           \tManage DCOS tasks

Get detailed command description with 'dcos <command> --help'.
""".encode('utf-8')

    assert_command(['dcos', 'help'],
                   stdout=stdout)
