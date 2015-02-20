import os
from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'help', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
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
    returncode, stdout, stderr = exec_command(['dcos', 'help', '--all'])

    assert returncode == 0
    assert stdout == """Available DCOS commands in '{}':

\tapp            \tDeploy and manage applications on Apache Mesos
\tconfig         \tGet and set DCOS command line options
\thelp           \tDisplay usage information
\tmarathon       \tDeploy and manage applications on Apache Mesos
\tpackage        \tInstall and manage DCOS software packages

Get detail command description with 'dcos <command> --help'.
""".format(os.path.join(os.environ['DCOS_PATH'], 'bin')).encode('utf-8')
    assert stderr == b''
