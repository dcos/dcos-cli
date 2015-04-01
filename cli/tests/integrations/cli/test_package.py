from common import exec_command


def test_package():
    returncode, stdout, stderr = exec_command(['dcos', 'package', '--help'])

    assert returncode == 0
    assert stdout == b"""Install and manage DCOS software packages

Usage:
    dcos package --config-schema
    dcos package describe <package_name>
    dcos package info
    dcos package install [--options=<options_file> --app-id=<app_id>]
         <package_name>
    dcos package list
    dcos package search <query>
    dcos package sources
    dcos package uninstall [--all | --app-id=<app-id>] <package_name>
    dcos package update

Options:
    -h, --help          Show this screen
    --version           Show version

Configuration:
    [package]
    # Path to the local package cache.
    cache_dir = "/var/dcos/cache"

    # List of package sources, in search order.
    #
    # Three protocols are supported:
    #   - Local file
    #   - HTTPS
    #   - Git
    sources = [
      "file:///Users/me/test-registry",
      "https://my.org/registry",
      "git://github.com/mesosphere/universe.git"
    ]
"""
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'package', 'info'])

    assert returncode == 0
    assert stdout == b'Install and manage DCOS software packages\n'
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', 'package', '--version'])

    assert returncode == 0
    assert stdout == b'dcos-package version 0.1.0\n'
    assert stderr == b''


def test_sources_list():
    returncode, stdout, stderr = exec_command(['dcos', 'package', 'sources'])

    assert returncode == 0
    assert stdout == b"""c3f1a0df1d2068e6b11d40224f5e500d3183a97e \
git://github.com/mesosphere/universe.git
f4ba0923d14eb75c1c0afca61c2adf9b2b355bd5 \
https://github.com/mesosphere/universe/archive/master.zip
"""
    assert stderr == b''


def test_update():
    returncode, stdout, stderr = exec_command(['dcos', 'package', 'update'])

    assert returncode == 0
    assert b'source' in stdout
    assert b'Validating package definitions...' in stdout
    assert b'OK' in stdout
    assert stderr == b''


def test_describe_nonexistent():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'describe', 'xyzzy'])

    assert returncode == 1
    assert stdout == b'Package [xyzzy] not found\n'
    assert stderr == b''


def test_describe():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'describe', 'mesos-dns'])

    assert returncode == 0
    assert b'description = "DNS-based service discovery for Mesos."' in stdout
    assert stderr == b''


def test_bad_install():
    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'install',
            'mesos-dns',
            '--options=tests/data/package/mesos-dns-config-bad.json'])

    assert returncode == 1
    assert stdout == b''

    assert stderr == b"""\
Error: 'mesos-dns/config-url' is a required property
Value: {"mesos-dns/host": false}

Error: False is not of type 'string'
Path: mesos-dns/host
Value: false
"""


def test_install():
    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'install',
            'mesos-dns',
            '--options=tests/data/package/mesos-dns-config.json'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def test_install_with_id():
    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'install',
            'mesos-dns',
            '--options=tests/data/package/mesos-dns-config.json',
            '--app-id=dns-1'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'install',
            'mesos-dns',
            '--options=tests/data/package/mesos-dns-config.json',
            '--app-id=dns-2'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def test_uninstall_with_id():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'uninstall', 'mesos-dns', '--app-id=dns-1'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def test_uninstall_all():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'uninstall', 'mesos-dns', '--all'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def test_uninstall_missing():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'uninstall', 'mesos-dns'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b'No instances of package [mesos-dns] are installed.\n'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'uninstall', 'mesos-dns', '--app-id=dns-1'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"""No instances of package [mesos-dns] with \
id [dns-1] are installed.\n"""


def test_list():
    returncode, stdout, stderr = exec_command(['dcos', 'package', 'list'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'install',
            'mesos-dns',
            '--options=tests/data/package/mesos-dns-config.json'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    returncode, stdout, stderr = exec_command(['dcos', 'package', 'list'])

    assert returncode == 0
    assert stdout == b'mesos-dns [alpha]\n'
    assert stderr == b''


def test_search():
    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'search',
            'framework'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert stderr == b''

    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'search',
            'xyzzy'])

    assert returncode == 0
    assert b'"packages": []' in stdout
    assert b'"source": "git://github.com/mesosphere/universe.git"' in stdout
    assert stderr == b''


def test_cleanup():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'uninstall', 'mesos-dns'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''
