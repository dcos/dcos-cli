from .helpers.common import assert_command


def test_info():
    stdout = b'Manage your DC/OS clusters\n'
    assert_command(['dcos', 'cluster', '--info'],
                   stdout=stdout)


def test_version():
    stdout = b'dcos-cluster version SNAPSHOT\n'
    assert_command(['dcos', 'cluster', '--version'],
                   stdout=stdout)
