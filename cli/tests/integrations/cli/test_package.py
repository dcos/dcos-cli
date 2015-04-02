import json

import six

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
    dcos package show <package_name> [--app-id=<app-id>]
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


def test_package_labels():
    app_labels = get_app_labels('mesos-dns')
    expected_metadata = b"""\
eyJkZXNjcmlwdGlvbiI6ICJETlMtYmFzZWQgc2VydmljZSBkaXNjb3ZlcnkgZm9yIE1lc29zLiIsI\
CJtYWludGFpbmVyIjogInN1cHBvcnRAbWVzb3NwaGVyZS5pbyIsICJuYW1lIjogIm1lc29zLWRucy\
IsICJwb3N0SW5zdGFsbE5vdGVzIjogIlBsZWFzZSByZWZlciB0byB0aGUgdHV0b3JpYWwgaW5zdHJ\
1Y3Rpb25zIGZvciBmdXJ0aGVyIHNldHVwIHJlcXVpcmVtZW50czogaHR0cDovL21lc29zcGhlcmUu\
Z2l0aHViLmlvL21lc29zLWRucy9kb2NzL3R1dG9yaWFsLWdjZS5odG1sIiwgInNjbSI6ICJodHRwc\
zovL2dpdGh1Yi5jb20vbWVzb3NwaGVyZS9tZXNvcy1kbnMuZ2l0IiwgInRhZ3MiOiBbIm1lc29zcG\
hlcmUiXSwgInZlcnNpb24iOiAiYWxwaGEiLCAid2Vic2l0ZSI6ICJodHRwOi8vbWVzb3NwaGVyZS5\
naXRodWIuaW8vbWVzb3MtZG5zIn0=\
"""
    actual_metadata = app_labels.get('DCOS_PACKAGE_METADATA')
    assert(six.b(actual_metadata) == expected_metadata)

    expected_registry_version = b'0.1.0-alpha'
    actual_registry_version = app_labels.get('DCOS_PACKAGE_REGISTRY_VERSION')
    assert(six.b(actual_registry_version) == expected_registry_version)

    expected_name = b'mesos-dns'
    actual_name = app_labels.get('DCOS_PACKAGE_NAME')
    assert(six.b(actual_name) == expected_name)

    expected_version = b'alpha'
    actual_version = app_labels.get('DCOS_PACKAGE_VERSION')
    assert(six.b(actual_version) == expected_version)

    expected_source = b'git://github.com/mesosphere/universe.git'
    actual_source = app_labels.get('DCOS_PACKAGE_SOURCE')
    assert(six.b(actual_source) == expected_source)


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


def test_show():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'show', 'mesos-dns'])

    assert returncode == 0
    assert stdout == b"""\
[
  {
    "endpoints": [],
    "id": "/mesos-dns",
    "name": "mesos-dns",
    "source": "git://github.com/mesosphere/universe.git",
    "version": "alpha"
  }
]
"""
    assert stderr == b''


def test_show_nonexistent():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'show', 'xyzzy'])

    assert returncode == 1
    assert b'No app found with package [xyzzy]' in stdout
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


def get_app_labels(app_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show', app_id])

    assert returncode == 0
    assert stderr == b''

    app_json = json.loads(stdout.decode('utf-8'))
    return app_json.get('labels')
