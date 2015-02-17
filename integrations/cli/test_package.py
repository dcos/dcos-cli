from common import exec_command


def test_package():
    returncode, stdout, stderr = exec_command(['dcos', 'package', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos package describe <package_name>
    dcos package info
    dcos package install [--options=<options_file>] <package_name>
    dcos package list
    dcos package search <query>
    dcos package sources
    dcos package uninstall <package_name>
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
"""
    assert stderr == b''


def test_update():
    returncode, stdout, stderr = exec_command(['dcos', 'package', 'update'])

    assert returncode == 0
    assert stdout.startswith(b'Validating package definitions...')
    assert stdout.endswith(b'OK\n')
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


def test_list():
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
        ['dcos', 'marathon', 'remove', 'mesos-dns'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''
