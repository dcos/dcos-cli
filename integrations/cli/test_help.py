import os

from dcos.api import util

from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'help', '--help'])

    assert returncode == 0
    assert stdout == b"""Display usage information

Usage:
    dcos help
    dcos help --all
    dcos help info

Options:
    --help              Show this screen
    --version           Show version
    --all               Prints all available commands to the standard output
"""
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'help', 'info'])

    assert returncode == 0
    assert stdout == b'Display usage information\n'
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', 'help', '--version'])

    assert returncode == 0
    assert stdout == b'dcos-help version 0.1.0\n'
    assert stderr == b''


def test_list_all():
    dcos_path = os.path.dirname(os.path.dirname(util.which('dcos')))
    returncode, stdout, stderr = exec_command(['dcos', 'help', '--all'])

    assert returncode == 0
    assert stdout == """Command line utility for \
the Mesosphere DataCenter Operating System (DCOS). The Mesosphere DCOS is \
a distributed operating system built around Apache Mesos. This utility \
provides tools for easy management of a DCOS installation.

Available DCOS commands in '{}':

\tconfig         \tGet and set DCOS command line options
\thelp           \tDisplay usage information
\tmarathon       \tDeploy and manage applications on the DCOS
\tmesos          \tInspect and manage the Apache Mesos installation
\tpackage        \tInstall and manage DCOS software packages
\tsubcommand     \tInstall and manage DCOS CLI Subcommands

Get detailed command description with 'dcos <command> --help'.
""".format(dcos_path).encode('utf-8')
    assert stderr == b''
