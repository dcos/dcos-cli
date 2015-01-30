from common import exec_command


def test_package():
    process = exec_command(['dcos', 'package', '--help'])
    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b"""Usage:
    dcos package info
    dcos package sources list
    dcos package update
    dcos package configure <package_name>
    dcos package search <query>
    dcos package install <package_name>
    dcos package uninstall <package_name>
    dcos package list

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
    process = exec_command(['dcos', 'package', 'info'])
    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b'Install and manage DCOS software packages.\n'
    assert stderr == b''


def test_version():
    process = exec_command(['dcos', 'package', '--version'])
    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stdout == b'dcos-package version 0.1.0\n'
    assert stderr == b''


def test_sources_list():
    process = exec_command(['dcos', 'package', 'sources', 'list'])
    stdout, stderr = process.communicate()

    print("stdout:")
    print(stdout.decode('utf-8'))

    print("stderr:")
    print(stderr.decode('utf-8'))

    assert process.returncode == 0
    assert stdout == b"""cc5af1bcaec7323400a95e1c38caf61378f6f081 \
file:///Users/me/test-registry
0c854fa7f2ede3dcc3122bf2b7db160491cf9f33 \
https://my.org/registry
c3f1a0df1d2068e6b11d40224f5e500d3183a97e \
git://github.com/mesosphere/universe.git
"""
    assert stderr == b''
