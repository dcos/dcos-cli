from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'mesos', '--help'])
    assert returncode == 0
    # Not checking stdout because this is an externally implemented CLI.
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'mesos', '--version'])
    assert returncode == 0
    assert stdout == b'dcos-mesos version 0.1.0\n'
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'mesos', 'info'])

    assert returncode == 0
    assert stdout == b'Inspect and manage the Apache Mesos installation\n'
    assert stderr == b''
