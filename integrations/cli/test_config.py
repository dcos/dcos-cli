import subprocess


def test_help():
    process = subprocess.Popen(
        ['dcos', 'config', '--help'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b"""Usage:
    dcos config info
    dcos config <name> [<value>]
    dcos config --unset <name>
    dcos config --list
    dcos config --help

Options:
    -h, --help            Show this screen
    --unset               Remove property from the config file
"""
    assert stderr == b''


def test_info():
    process = subprocess.Popen(
        ['dcos', 'config', 'info'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b'Get and set DCOS command line options\n'
    assert stderr == b''


def test_list_property():
    process = subprocess.Popen(
        ['dcos', 'config', '--list'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b"""marathon.port=8080
marathon.host=localhost
"""
    assert stderr == b''


def test_get_exisiting_property():
    _get_value('marathon.host', 'localhost')


def test_get_missing_proerty():
    _get_missing_value('missing.property')


def test_set_existing_property():
    _set_value('marathon.host', 'newhost')
    _get_value('marathon.host', 'newhost')
    _set_value('marathon.host', 'localhost')


def test_unset_property():
    _unset_value('marathon.host')
    _get_missing_value('marathon.host')
    _set_value('marathon.host', 'localhost')


def test_set_missing_property():
    _set_value('path.to.value', 'cool new value')
    _get_value('path.to.value', 'cool new value')
    _unset_value('path.to.value')


def _set_value(key, value):
    process = subprocess.Popen(
        ['dcos', 'config', key, value],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b''
    assert stderr == b''


def _get_value(key, value):
    process = subprocess.Popen(
        ['dcos', 'config', key],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b'{}\n'.format(value)
    assert stderr == b''


def _unset_value(key):
    process = subprocess.Popen(
        ['dcos', 'config', '--unset', key],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b''
    assert stderr == b''


def _get_missing_value(key):
    process = subprocess.Popen(
        ['dcos', 'config', key],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    assert process.returncode == 1
    assert stdout == b''
    assert stderr == b''
