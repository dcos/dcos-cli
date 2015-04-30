import json
import os

import six
from dcos import subcommand

from common import assert_command, exec_command


def test_package():
    stdout = b"""Install and manage DCOS software packages

Usage:
    dcos package --config-schema
    dcos package --info
    dcos package describe <package_name>
    dcos package info
    dcos package install [--cli | [--app --app-id=<app_id]]
                         [--options=<file>]
                 <package_name>
    dcos package list-installed [--endpoints --app-id=<app-id> <package_name>]
    dcos package search [<query>]
    dcos package sources
    dcos package uninstall [--cli | [--app --app-id=<app-id> --all]]
                 <package_name>
    dcos package update [--validate]

Options:
    -h, --help         Show this screen
    --info             Show a short description of this subcommand
    --version          Show version
    --all              Apply the operation to all matching packages
    --app              Apply the operation only to the package's application
    --app-id=<app-id>  The application id
    --cli              Apply the operation only to the package's CLI
    --options=<file>   Path to a JSON file containing package installation
                       options
    --validate         Validate package content when updating sources

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
    assert_command(['dcos', 'package', '--help'],
                   stdout=stdout)


def test_info():
    assert_command(['dcos', 'package', '--info'],
                   stdout=b'Install and manage DCOS software packages\n')


def test_version():
    assert_command(['dcos', 'package', '--version'],
                   stdout=b'dcos-package version SNAPSHOT\n')


def test_sources_list():
    stdout = b"""c3f1a0df1d2068e6b11d40224f5e500d3183a97e \
git://github.com/mesosphere/universe.git
f4ba0923d14eb75c1c0afca61c2adf9b2b355bd5 \
https://github.com/mesosphere/universe/archive/master.zip
"""
    assert_command(['dcos', 'package', 'sources'],
                   stdout=stdout)


def test_update_without_validation():
    returncode, stdout, stderr = exec_command(['dcos', 'package', 'update'])

    assert returncode == 0
    assert b'source' in stdout
    assert b'Validating package definitions...' not in stdout
    assert b'OK' not in stdout
    assert stderr == b''


def test_update_with_validation():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'update', '--validate'])

    assert returncode == 0
    assert b'source' in stdout
    assert b'Validating package definitions...' in stdout
    assert b'OK' in stdout
    assert stderr == b''


def test_describe_nonexistent():
    assert_command(['dcos', 'package', 'describe', 'xyzzy'],
                   stdout=b'Package [xyzzy] not found\n',
                   returncode=1)


def test_describe():
    stdout = b"""\
{
  "description": "DNS-based service discovery for Mesos.",
  "maintainer": "support@mesosphere.io",
  "name": "mesos-dns",
  "postInstallNotes": "Please refer to the tutorial instructions for further \
setup requirements: http://mesosphere.github.io/mesos-dns/docs/\
tutorial-gce.html",
  "scm": "https://github.com/mesosphere/mesos-dns.git",
  "tags": [
    "mesosphere"
  ],
  "versions": [
    "alpha"
  ],
  "website": "http://mesosphere.github.io/mesos-dns"
}
"""
    assert_command(['dcos', 'package', 'describe', 'mesos-dns'],
                   stdout=stdout)


def test_bad_install():
    args = ['--options=tests/data/package/mesos-dns-config-bad.json']
    stderr = b"""\
Error: missing required property 'mesos-dns/config-url'. \
Add to JSON file and pass in /path/to/file with the --options argument.

Error: False is not of type 'string'
Path: mesos-dns/host
Value: false
"""
    assert_command(['dcos', 'package', 'install', 'mesos-dns', args[0]],
                   returncode=1,
                   stderr=stderr)

    _install_mesos_dns(args=args,
                       returncode=1,
                       stdout=b'',
                       stderr=stderr)


def test_install():
    _install_mesos_dns()


def test_package_metadata():
    _install_helloworld()

    # test marathon labels
    expected_metadata = b"""eyJkZXNjcmlwdGlvbiI6ICJFeGFtcGxlIERDT1MgYXBwbGljYX\
Rpb24gcGFja2FnZSIsICJtYWludGFpbmVyIjogInN1cHBvcnRAbWVzb3NwaGVyZS5pbyIsICJuYW1l\
IjogImhlbGxvd29ybGQiLCAidGFncyI6IFsibWVzb3NwaGVyZSIsICJleGFtcGxlIiwgInN1YmNvbW\
1hbmQiXSwgInZlcnNpb24iOiAiMC4xLjAiLCAid2Vic2l0ZSI6ICJodHRwczovL2dpdGh1Yi5jb20v\
bWVzb3NwaGVyZS9kY29zLWhlbGxvd29ybGQifQ=="""

    expected_command = b"""eyJwaXAiOiBbImh0dHA6Ly9kb3dubG9hZHMubWVzb3NwaGVyZS5\
pby9kY29zLWNsaS9kY29zLTAuMS4wLXB5Mi5weTMtbm9uZS1hbnkud2hsIiwgImdpdCtodHRwczovL\
2dpdGh1Yi5jb20vbWVzb3NwaGVyZS9kY29zLWhlbGxvd29ybGQuZ2l0I2Rjb3MtaGVsbG93b3JsZD0\
wLjEuMCJdfQ=="""

    expected_source = b'git://github.com/mesosphere/universe.git'

    expected_labels = {
        'DCOS_PACKAGE_METADATA': expected_metadata,
        'DCOS_PACKAGE_COMMAND': expected_command,
        'DCOS_PACKAGE_REGISTRY_VERSION': b'0.1.0-alpha',
        'DCOS_PACKAGE_NAME': b'helloworld',
        'DCOS_PACKAGE_VERSION': b'0.1.0',
        'DCOS_PACKAGE_SOURCE': expected_source,
        'DCOS_PACKAGE_RELEASE': b'0',
    }

    app_labels = get_app_labels('helloworld')

    for label, value in expected_labels.items():
        assert value == six.b(app_labels.get(label))

    # test local package.json
    package = {
        "website": "https://github.com/mesosphere/dcos-helloworld",
        "maintainer": "support@mesosphere.io",
        "name": "helloworld",
        "tags": ["mesosphere", "example", "subcommand"],
        "version": "0.1.0",
        "description": "Example DCOS application package"
    }

    package_dir = subcommand.package_dir('helloworld')

    # test local package.json
    package_path = os.path.join(package_dir, 'package.json')
    with open(package_path) as f:
        assert json.load(f) == package

    # test local source
    source_path = os.path.join(package_dir, 'source')
    with open(source_path) as f:
        assert six.b(f.read()) == expected_source

    # test local version
    version_path = os.path.join(package_dir, 'version')
    with open(version_path) as f:
        assert six.b(f.read()) == b'0'

    # uninstall helloworld
    _uninstall_helloworld()


def test_install_with_id():
    args = ['--options=tests/data/package/mesos-dns-config.json',
            '--app-id=dns-1']
    stdout = b"""Installing package [mesos-dns] version [alpha] \
with app id [dns-1]\n"""
    _install_mesos_dns(args=args, stdout=stdout)

    args = ['--options=tests/data/package/mesos-dns-config.json',
            '--app-id=dns-2']
    stdout = b"""Installing package [mesos-dns] version [alpha] \
with app id [dns-2]\n"""
    _install_mesos_dns(args=args, stdout=stdout)


def test_install_missing_package():
    stderr = b"""Package [missing-package] not found
You may need to run 'dcos package update' to update your repositories
"""
    assert_command(['dcos', 'package', 'install', 'missing-package'],
                   returncode=1,
                   stderr=stderr)


def test_uninstall_with_id():
    _uninstall_mesos_dns(args=['--app-id=dns-1'])


def test_uninstall_all():
    _uninstall_mesos_dns(args=['--all'])


def test_uninstall_missing():
    stderr = b'Package [mesos-dns] is not installed.\n'
    _uninstall_mesos_dns(returncode=1, stderr=stderr)

    stderr = b'Package [mesos-dns] with id [dns-1] is not installed.\n'
    _uninstall_mesos_dns(args=['--app-id=dns-1'], returncode=1, stderr=stderr)


def test_uninstall_subcommand():
    _install_helloworld()
    _uninstall_helloworld()

    assert_command(['dcos', 'package', 'list-installed'], stdout=b'[]\n')


def test_uninstall_cli():
    _install_helloworld()
    _uninstall_helloworld(args=['--cli'])

    stdout = b"""[
  {
    "app": {
      "appId": "/helloworld"
    },
    "description": "Example DCOS application package",
    "maintainer": "support@mesosphere.io",
    "name": "helloworld",
    "packageSource": "git://github.com/mesosphere/universe.git",
    "releaseVersion": "0",
    "tags": [
      "mesosphere",
      "example",
      "subcommand"
    ],
    "version": "0.1.0",
    "website": "https://github.com/mesosphere/dcos-helloworld"
  }
]
"""
    assert_command(['dcos', 'package', 'list-installed'],
                   stdout=stdout)

    _uninstall_helloworld()


def test_list_installed():
    assert_command(['dcos', 'package', 'list-installed'],
                   stdout=b'[]\n')

    assert_command(['dcos', 'package', 'list-installed', 'xyzzy'],
                   stdout=b'[]\n')

    assert_command(['dcos', 'package', 'list-installed', '--app-id=/xyzzy'],
                   stdout=b'[]\n')

    _install_mesos_dns()

    expected_output = b"""\
[
  {
    "app": {
      "appId": "/mesos-dns"
    },
    "description": "DNS-based service discovery for Mesos.",
    "maintainer": "support@mesosphere.io",
    "name": "mesos-dns",
    "packageSource": "git://github.com/mesosphere/universe.git",
    "postInstallNotes": "Please refer to the tutorial instructions for \
further setup requirements: http://mesosphere.github.io/mesos-dns/docs\
/tutorial-gce.html",
    "releaseVersion": "0",
    "scm": "https://github.com/mesosphere/mesos-dns.git",
    "tags": [
      "mesosphere"
    ],
    "version": "alpha",
    "website": "http://mesosphere.github.io/mesos-dns"
  }
]
"""
    assert_command(['dcos', 'package', 'list-installed'],
                   stdout=expected_output)

    assert_command(['dcos', 'package', 'list-installed', 'mesos-dns'],
                   stdout=expected_output)

    assert_command(
        ['dcos', 'package', 'list-installed', '--app-id=/mesos-dns'],
        stdout=expected_output)

    assert_command(
        ['dcos', 'package', 'list-installed', 'ceci-nest-pas-une-package'],
        stdout=b'[]\n')

    assert_command(
        ['dcos', 'package', 'list-installed',
         '--app-id=/ceci-nest-pas-une-package'],
        stdout=b'[]\n')

    _uninstall_mesos_dns()


def test_list_installed_cli():
    _install_helloworld()

    stdout = b"""\
[
  {
    "app": {
      "appId": "/helloworld"
    },
    "command": {
      "name": "helloworld"
    },
    "description": "Example DCOS application package",
    "maintainer": "support@mesosphere.io",
    "name": "helloworld",
    "packageSource": "git://github.com/mesosphere/universe.git",
    "releaseVersion": "0",
    "tags": [
      "mesosphere",
      "example",
      "subcommand"
    ],
    "version": "0.1.0",
    "website": "https://github.com/mesosphere/dcos-helloworld"
  }
]
"""
    assert_command(['dcos', 'package', 'list-installed'],
                   stdout=stdout)

    _uninstall_helloworld()

    stdout = b"Installing CLI subcommand for package [helloworld]\n"
    _install_helloworld(args=['--cli'], stdout=stdout)

    stdout = b"""\
[
  {
    "command": {
      "name": "helloworld"
    },
    "description": "Example DCOS application package",
    "maintainer": "support@mesosphere.io",
    "name": "helloworld",
    "packageSource": "git://github.com/mesosphere/universe.git",
    "releaseVersion": "0",
    "tags": [
      "mesosphere",
      "example",
      "subcommand"
    ],
    "version": "0.1.0",
    "website": "https://github.com/mesosphere/dcos-helloworld"
  }
]
"""
    assert_command(['dcos', 'package', 'list-installed'],
                   stdout=stdout)

    _uninstall_helloworld()


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

    returncode, stdout, stderr = exec_command(
        ['dcos',
            'package',
            'search'])

    registries = json.loads(stdout.decode('utf-8'))
    for registry in registries:
        # assert the number of packages is gte the number at the time
        # this test was written
        assert len(registry['packages']) >= 9

    assert returncode == 0
    assert stderr == b''


def get_app_labels(app_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show', app_id])

    assert returncode == 0
    assert stderr == b''

    app_json = json.loads(stdout.decode('utf-8'))
    return app_json.get('labels')


def _install_helloworld(
        args=[],
        stdout=b"""Installing package [helloworld] version [0.1.0]
Installing CLI subcommand for package [helloworld]
"""):
    assert_command(['dcos', 'package', 'install', 'helloworld'] + args,
                   stdout=stdout)


def _uninstall_helloworld(args=[]):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld'] + args)


def _uninstall_mesos_dns(args=[],
                         returncode=0,
                         stdout=b'',
                         stderr=b''):
    cmd = ['dcos', 'package', 'uninstall', 'mesos-dns'] + args
    assert_command(cmd, returncode, stdout, stderr)


def _install_mesos_dns(
        args=['--options=tests/data/package/mesos-dns-config.json'],
        returncode=0,
        stdout=b'Installing package [mesos-dns] version [alpha]\n',
        stderr=b''):

    cmd = ['dcos', 'package', 'install', 'mesos-dns'] + args
    assert_command(cmd, returncode, stdout, stderr)
