from .common import assert_command, exec_command


def test_default():
    with open('tests/data/help/default.txt') as content:
        assert_command(['dcos'],
                       stdout=content.read().encode('utf-8'))


def test_help():
    with open('tests/data/help/dcos.txt') as content:
        assert_command(['dcos', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_version():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--version'])

    assert returncode == 0
    assert stderr == b''
    versions = stdout.decode('utf-8').split("\n")
    assert versions[0] == "dcoscli.version=SNAPSHOT"
    assert versions[1].startswith("dcos.version")
    assert versions[2].startswith("dcos.commit")
    assert versions[3].startswith("dcos.bootstrap-id")


def test_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=info', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Manage the DC/OS configuration file\n"


def test_capital_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=INFO', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Manage the DC/OS configuration file\n"


def test_invalid_log_level_flag():
    stdout = (b"Log level set to an unknown value 'blah'. Valid "
              b"values are ['debug', 'info', 'warning', 'error', "
              b"'critical']\n")

    assert_command(
        ['dcos', '--log-level=blah', 'config', '--info'],
        returncode=1,
        stdout=stdout)
