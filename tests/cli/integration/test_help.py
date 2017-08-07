from ..helpers.common import assert_command


def test_help():
    with open('dcos/cli/data/help/help.txt') as content:
        assert_command(['dcos', 'help', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    assert_command(['dcos', 'help', '--info'],
                   stdout=b'Display help information about DC/OS\n')


def test_version():
    assert_command(['dcos', 'help', '--version'],
                   stdout=b'dcos-help version SNAPSHOT\n')


def test_help_config():
    with open('dcos/cli/data/help/config.txt') as content:
        assert_command(['dcos', 'help', 'config'],
                       stdout=content.read().encode('utf-8'))


def test_help_job():
    with open('dcos/cli/data/help/job.txt') as content:
        assert_command(['dcos', 'help', 'job'],
                       stdout=content.read().encode('utf-8'))


def test_help_marathon():
    with open('dcos/cli/data/help/marathon.txt') as content:
        assert_command(['dcos', 'help', 'marathon'],
                       stdout=content.read().encode('utf-8'))


def test_help_node():
    with open('dcos/cli/data/help/node.txt') as content:
        assert_command(['dcos', 'help', 'node'],
                       stdout=content.read().encode('utf-8'))


def test_help_package():
    with open('dcos/cli/data/help/package.txt') as content:
        assert_command(['dcos', 'help', 'package'],
                       stdout=content.read().encode('utf-8'))


def test_help_service():
    with open('dcos/cli/data/help/service.txt') as content:
        assert_command(['dcos', 'help', 'service'],
                       stdout=content.read().encode('utf-8'))


def test_help_task():
    with open('dcos/cli/data/help/task.txt') as content:
        assert_command(['dcos', 'help', 'task'],
                       stdout=content.read().encode('utf-8'))


def test_help_auth():
    with open('dcos/cli/data/help/auth.txt') as content:
        assert_command(['dcos', 'help', 'auth'],
                       stdout=content.read().encode('utf-8'))
