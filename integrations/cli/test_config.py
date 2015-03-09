import os

import pytest
from common import exec_command


@pytest.fixture
def env():
    return {
        'PATH': os.environ['PATH'],
        'DCOS_PATH': os.environ['DCOS_PATH'],
        'DCOS_CONFIG': os.path.join("tests", "data", "Dcos.toml")
    }


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'config', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos config info
    dcos config <name> [<value>]
    dcos config --unset <name>
    dcos config --list

Options:
    -h, --help            Show this screen
    --version             Show version
    --unset               Remove property from the config file
"""
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'config', 'info'])

    assert returncode == 0
    assert stdout == b'Get and set DCOS command line options\n'
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', 'config', '--version'])

    assert returncode == 0
    assert stdout == b'dcos-config version 0.1.0\n'
    assert stderr == b''


def test_list_property(env):
    returncode, stdout, stderr = exec_command(['dcos', 'config', '--list'],
                                              env)
    assert returncode == 0
    assert stdout == b"""marathon.host=localhost
marathon.port=8080
package.cache=tmp/cache
package.sources=['git://github.com/mesosphere/universe.git', \
'https://github.com/mesosphere/universe/archive/master.zip']
"""
    assert stderr == b''


def test_get_existing_property(env):
    _get_value('marathon.host', 'localhost', env)


def test_get_missing_proerty(env):
    _get_missing_value('missing.property', env)


def test_set_existing_property(env):
    _set_value('marathon.host', 'newhost', env)
    _get_value('marathon.host', 'newhost', env)
    _set_value('marathon.host', 'localhost', env)


def test_unset_property(env):
    _unset_value('marathon.host', env)
    _get_missing_value('marathon.host', env)
    _set_value('marathon.host', 'localhost', env)


def test_set_missing_property(env):
    _set_value('path.to.value', 'cool new value', env)
    _get_value('path.to.value', 'cool new value', env)
    _unset_value('path.to.value', env)


def _set_value(key, value, env):
    returncode, stdout, stderr = exec_command(['dcos', 'config', key, value],
                                              env)
    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _get_value(key, value, env):
    returncode, stdout, stderr = exec_command(['dcos', 'config', key],
                                              env)
    assert returncode == 0
    assert stdout == '{}\n'.format(value).encode('utf-8')
    assert stderr == b''


def _unset_value(key, env):
    returncode, stdout, stderr = exec_command(['dcos',
                                               'config',
                                               '--unset',
                                               key],
                                              env)
    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _get_missing_value(key, env):
    returncode, stdout, stderr = exec_command(['dcos', 'config', key],
                                              env)
    assert returncode == 1
    assert stdout == b''
    assert stderr == b''
