import contextlib
import json
import os

import six
from dcos import subcommand

import pytest

from .common import (assert_command, assert_lines, delete_zk_nodes,
                     exec_command, file_bytes, get_services, service_shutdown,
                     watch_all_deployments)


@pytest.fixture(scope="module")
def zk_znode(request):
    request.addfinalizer(delete_zk_nodes)
    return request


def _chronos_description(app_ids):
    """
    :param app_ids: a list of application id
    :type app_ids: [str]
    :returns: a binary string representing the chronos description
    :rtype: str
    """

    result = [
        {"apps": app_ids,
         "description": "A fault tolerant job scheduler for Mesos which "
                        "handles dependencies and ISO8601 based schedules.",
         "framework": True,
         "images": {
             "icon-large": "https://downloads.mesosphere.io/chronos/assets/"
                           "icon-service-chronos-large.png",
             "icon-medium": "https://downloads.mesosphere.io/chronos/assets/"
                            "icon-service-chronos-medium.png",
             "icon-small": "https://downloads.mesosphere.io/chronos/assets/"
                           "icon-service-chronos-small.png"
         },
         "licenses": [
             {
                 "name": "Apache License Version 2.0",
                 "url": "https://github.com/mesos/chronos/blob/master/LICENSE"
             }
         ],
         "maintainer": "support@mesosphere.io",
         "name": "chronos",
         "packageSource": "https://github.com/mesosphere/universe/archive/\
version-1.x.zip",
         "postInstallNotes": "Chronos DCOS Service has been successfully "
                             "installed!\n\n\tDocumentation: http://mesos."
                             "github.io/chronos\n\tIssues: https://github.com/"
                             "mesos/chronos/issues",
         "postUninstallNotes": "The Chronos DCOS Service has been uninstalled "
                               "and will no longer run.\nPlease follow the "
                               "instructions at http://docs.mesosphere."
                               "com/services/chronos/#uninstall to clean up "
                               "any persisted state",
         "preInstallNotes": "We recommend a minimum of one node with at least "
                            "1 CPU and 2GB of RAM available for the Chronos "
                            "Service.",
         "releaseVersion": "0",
         "scm": "https://github.com/mesos/chronos.git",
         "tags": [
             "mesosphere",
             "framework"
         ],
         "version": "2.3.4"
         }]

    return (json.dumps(result, sort_keys=True, indent=2).replace(' \n', '\n') +
            '\n').encode('utf-8')


def test_package():
    stdout = b"""Install and manage DCOS software packages

Usage:
    dcos package --config-schema
    dcos package --info
    dcos package describe [--app --options=<file> --cli] <package_name>
    dcos package install [--cli | [--app --app-id=<app_id>]]
                         [--options=<file> --yes] <package_name>
    dcos package list [--json --endpoints --app-id=<app-id> <package_name>]
                      [--colors]
    dcos package search [--json <query> --colors]
    dcos package sources
    dcos package uninstall [--cli | [--app --app-id=<app-id> --all]]
                 <package_name>
    dcos package update [--validate]

Options:
    -h, --help         Show this screen
    --info             Show a short description of this subcommand
    --version          Show version
    --yes              Assume "yes" is the answer to all prompts and run
                       non-interactively
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
    stdout = b"""a1a3267044fd65760dbfcdbe221c81e04e512657 \
https://github.com/mesosphere/universe/archive/version-1.x.zip
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
                   stderr=b'Package [xyzzy] not found\n',
                   returncode=1)


def test_describe():
    stdout = file_bytes(
        'tests/data/package/json/test_describe_marathon.json')
    assert_command(['dcos', 'package', 'describe', 'marathon'],
                   stdout=stdout)

    stdout = file_bytes(
        'tests/data/package/json/test_describe_cli_helloworld.json')
    assert_command(['dcos', 'package', 'describe', '--cli', 'helloworld'],
                   stdout=stdout)

    stdout = file_bytes(
        'tests/data/package/json/test_describe_app_marathon.json')
    assert_command(['dcos', 'package', 'describe', '--app', '--options',
                    'tests/data/package/marathon.json', 'marathon'],
                   stdout=stdout)


def test_bad_install():
    args = ['--options=tests/data/package/chronos-bad.json', '--yes']
    stderr = b"""Error: False is not of type 'string'
Path: chronos.zk-hosts
Value: false

Please create a JSON file with the appropriate options, and pass the \
/path/to/file as an --options argument.
"""

    _install_chronos(args=args,
                     returncode=1,
                     stdout=b'',
                     stderr=stderr,
                     postInstallNotes=b'')


def test_install(zk_znode):
    _install_chronos()
    watch_all_deployments()
    _uninstall_chronos()
    get_services(expected_count=1, args=['--inactive'])


def test_install_missing_options_file():
    """Test that a missing options file results in the expected stderr
    message."""
    assert_command(
        ['dcos', 'package', 'install', 'chronos', '--yes',
         '--options=asdf.json'],
        returncode=1,
        stdout=b'We recommend a minimum of one node with at least 1 CPU and '
               b'2GB of RAM available for the Chronos Service.\n',
        stderr=b"Error opening file [asdf.json]: No such file or directory\n")


def test_package_metadata():
    _install_helloworld()

    # test marathon labels
    expected_metadata = b"""eyJkZXNjcmlwdGlvbiI6ICJFeGFtcGxlIERDT1MgYXBwbGljYX\
Rpb24gcGFja2FnZSIsICJtYWludGFpbmVyIjogInN1cHBvcnRAbWVzb3NwaGVyZS5pbyIsICJuYW1l\
IjogImhlbGxvd29ybGQiLCAicG9zdEluc3RhbGxOb3RlcyI6ICJBIHNhbXBsZSBwb3N0LWluc3RhbG\
xhdGlvbiBtZXNzYWdlIiwgInByZUluc3RhbGxOb3RlcyI6ICJBIHNhbXBsZSBwcmUtaW5zdGFsbGF0\
aW9uIG1lc3NhZ2UiLCAidGFncyI6IFsibWVzb3NwaGVyZSIsICJleGFtcGxlIiwgInN1YmNvbW1hbm\
QiXSwgInZlcnNpb24iOiAiMC4xLjAiLCAid2Vic2l0ZSI6ICJodHRwczovL2dpdGh1Yi5jb20vbWVz\
b3NwaGVyZS9kY29zLWhlbGxvd29ybGQifQ=="""

    expected_command = b"""eyJwaXAiOiBbImRjb3M8MS4wIiwgImdpdCtodHRwczovL2dpdGh\
1Yi5jb20vbWVzb3NwaGVyZS9kY29zLWhlbGxvd29ybGQuZ2l0I2Rjb3MtaGVsbG93b3JsZD0wLjEuM\
CJdfQ=="""

    expected_source = b'https://github.com/mesosphere/universe/archive/\
version-1.x.zip'

    expected_labels = {
        'DCOS_PACKAGE_METADATA': expected_metadata,
        'DCOS_PACKAGE_COMMAND': expected_command,
        'DCOS_PACKAGE_REGISTRY_VERSION': b'1.0.0-rc1',
        'DCOS_PACKAGE_NAME': b'helloworld',
        'DCOS_PACKAGE_VERSION': b'0.1.0',
        'DCOS_PACKAGE_SOURCE': expected_source,
        'DCOS_PACKAGE_RELEASE': b'0',
    }

    app_labels = _get_app_labels('helloworld')

    for label, value in expected_labels.items():
        assert value == six.b(app_labels.get(label))

    # test local package.json
    package = {
        "description": "Example DCOS application package",
        "maintainer": "support@mesosphere.io",
        "name": "helloworld",
        "postInstallNotes": "A sample post-installation message",
        "preInstallNotes": "A sample pre-installation message",
        "tags": ["mesosphere", "example", "subcommand"],
        "version": "0.1.0",
        "website": "https://github.com/mesosphere/dcos-helloworld",
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


def test_install_with_id(zk_znode):
    args = ['--app-id=chronos-1', '--yes']
    stdout = (b'Installing package [chronos] version [2.3.4] with app id '
              b'[chronos-1]\n')
    _install_chronos(args=args, stdout=stdout)

    args = ['--app-id=chronos-2', '--yes']
    stdout = (b'Installing package [chronos] version [2.3.4] with app id '
              b'[chronos-2]\n')
    _install_chronos(args=args, stdout=stdout)


def test_install_missing_package():
    stderr = b"""Package [missing-package] not found
You may need to run 'dcos package update' to update your repositories
"""
    assert_command(['dcos', 'package', 'install', 'missing-package'],
                   returncode=1,
                   stderr=stderr)


def test_uninstall_with_id(zk_znode):
    _uninstall_chronos(args=['--app-id=chronos-1'])


def test_uninstall_all(zk_znode):
    _uninstall_chronos(args=['--all'])
    get_services(expected_count=1, args=['--inactive'])


def test_uninstall_missing():
    stderr = 'Package [chronos] is not installed.\n'
    _uninstall_chronos(returncode=1, stderr=stderr)

    stderr = 'Package [chronos] with id [chronos-1] is not installed.\n'
    _uninstall_chronos(
        args=['--app-id=chronos-1'],
        returncode=1,
        stderr=stderr)


def test_uninstall_subcommand():
    _install_helloworld()
    _uninstall_helloworld()
    _list()


def test_uninstall_cli():
    _install_helloworld()
    _uninstall_helloworld(args=['--cli'])

    stdout = b"""[
  {
    "apps": [
      "/helloworld"
    ],
    "description": "Example DCOS application package",
    "maintainer": "support@mesosphere.io",
    "name": "helloworld",
    "packageSource": "https://github.com/mesosphere/universe/archive/\
version-1.x.zip",
    "postInstallNotes": "A sample post-installation message",
    "preInstallNotes": "A sample pre-installation message",
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
    _list(stdout=stdout)
    _uninstall_helloworld()


def test_uninstall_multiple_apps():
    stdout = (b'A sample pre-installation message\n'
              b'Installing package [helloworld] version [0.1.0] ' +
              b'with app id [/helloworld-1]\n'
              b'Installing CLI subcommand for package [helloworld]\n'
              b'New command available: dcos helloworld\n'
              b'A sample post-installation message\n')

    _install_helloworld(['--yes', '--app-id=/helloworld-1'],
                        stdout=stdout)

    stdout = (b'A sample pre-installation message\n'
              b'Installing package [helloworld] version [0.1.0] ' +
              b'with app id [/helloworld-2]\n'
              b'Installing CLI subcommand for package [helloworld]\n'
              b'New command available: dcos helloworld\n'
              b'A sample post-installation message\n')

    _install_helloworld(['--yes', '--app-id=/helloworld-2'],
                        stdout=stdout)

    stderr = (b"Multiple apps named [helloworld] are installed: " +
              b"[/helloworld-1, /helloworld-2].\n" +
              b"Please use --app-id to specify the ID of the app " +
              b"to uninstall, or use --all to uninstall all apps.\n")
    _uninstall_helloworld(stderr=stderr,
                          returncode=1)

    assert_command(['dcos', 'package', 'uninstall', 'helloworld', '--all'])

    watch_all_deployments()


def test_list(zk_znode):
    _list()
    _list(args=['xyzzy', '--json'])
    _list(args=['--app-id=/xyzzy', '--json'])

    _install_chronos()
    expected_output = _chronos_description(['/chronos'])

    _list(stdout=expected_output)
    _list(args=['--json', 'chronos'],
          stdout=expected_output)
    _list(args=['--json', '--app-id=/chronos'],
          stdout=expected_output)
    _list(args=['--json', 'ceci-nest-pas-une-package'])
    _list(args=['--json', '--app-id=/ceci-nest-pas-une-package'])

    _uninstall_chronos()


def test_list_table():
    with _helloworld():
        assert_lines(['dcos', 'package', 'list'], 2)


def test_install_yes():
    with open('tests/data/package/assume_yes.txt') as yes_file:
        _install_helloworld(
            args=[],
            stdin=yes_file,
            stdout=b'A sample pre-installation message\n'
                   b'Continue installing? [yes/no] '
                   b'Installing package [helloworld] version [0.1.0]\n'
                   b'Installing CLI subcommand for package [helloworld]\n'
                   b'New command available: dcos helloworld\n'
                   b'A sample post-installation message\n')
        _uninstall_helloworld()


def test_install_no():
    with open('tests/data/package/assume_no.txt') as no_file:
        _install_helloworld(
            args=[],
            stdin=no_file,
            stdout=b'A sample pre-installation message\n'
                   b'Continue installing? [yes/no] Exiting installation.\n')


def test_list_cli():
    _install_helloworld()

    stdout = b"""\
[
  {
    "apps": [
      "/helloworld"
    ],
    "command": {
      "name": "helloworld"
    },
    "description": "Example DCOS application package",
    "maintainer": "support@mesosphere.io",
    "name": "helloworld",
    "packageSource": "https://github.com/mesosphere/universe/archive/\
version-1.x.zip",
    "postInstallNotes": "A sample post-installation message",
    "preInstallNotes": "A sample pre-installation message",
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
    _list(stdout=stdout)
    _uninstall_helloworld()

    stdout = (b"A sample pre-installation message\n"
              b"Installing CLI subcommand for package [helloworld]\n"
              b'New command available: dcos helloworld\n'
              b"A sample post-installation message\n")
    _install_helloworld(args=['--cli', '--yes'], stdout=stdout)

    stdout = b"""\
[
  {
    "command": {
      "name": "helloworld"
    },
    "description": "Example DCOS application package",
    "maintainer": "support@mesosphere.io",
    "name": "helloworld",
    "packageSource": "https://github.com/mesosphere/universe/archive/\
version-1.x.zip",
    "postInstallNotes": "A sample post-installation message",
    "preInstallNotes": "A sample pre-installation message",
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
    _list(stdout=stdout)
    _uninstall_helloworld()


def test_uninstall_multiple_frameworknames(zk_znode):
    _install_chronos(
        args=['--yes', '--options=tests/data/package/chronos-1.json'])
    _install_chronos(
        args=['--yes', '--options=tests/data/package/chronos-2.json'])

    watch_all_deployments()

    expected_output = _chronos_description(
        ['/chronos-user-1', '/chronos-user-2'])

    _list(stdout=expected_output)
    _list(args=['--json', 'chronos'], stdout=expected_output)
    _list(args=['--json', '--app-id=/chronos-user-1'],
          stdout=_chronos_description(['/chronos-user-1']))
    _list(args=['--json', '--app-id=/chronos-user-2'],
          stdout=_chronos_description(['/chronos-user-2']))
    _uninstall_chronos(
        args=['--app-id=chronos-user-1'],
        returncode=1,
        stderr='Unable to shutdown the framework for [chronos-user] because '
               'there are multiple frameworks with the same name: ')
    _uninstall_chronos(
        args=['--app-id=chronos-user-2'],
        returncode=1,
        stderr='Unable to shutdown the framework for [chronos-user] because '
               'there are multiple frameworks with the same name: ')

    for framework in get_services(args=['--inactive']):
        if framework['name'] == 'chronos-user':
            service_shutdown(framework['id'])


def test_search():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', 'framework', '--json'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert stderr == b''

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', 'xyzzy', '--json'])

    assert returncode == 0
    assert b'"packages": []' in stdout
    assert b'"source": "https://github.com/mesosphere/universe/archive/\
version-1.x.zip"' in stdout
    assert stderr == b''

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', '--json'])

    registries = json.loads(stdout.decode('utf-8'))
    for registry in registries:
        # assert the number of packages is gte the number at the time
        # this test was written
        assert len(registry['packages']) >= 5

    assert returncode == 0
    assert stderr == b''


def test_search_table():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert len(stdout.decode('utf-8').split('\n')) > 5
    assert stderr == b''


def _get_app_labels(app_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show', app_id])

    assert returncode == 0
    assert stderr == b''

    app_json = json.loads(stdout.decode('utf-8'))
    return app_json.get('labels')


def _install_helloworld(
        args=['--yes'],
        stdout=b'A sample pre-installation message\n'
               b'Installing package [helloworld] version [0.1.0]\n'
               b'Installing CLI subcommand for package [helloworld]\n'
               b'New command available: dcos helloworld\n'
               b'A sample post-installation message\n',
        returncode=0,
        stdin=None):
    assert_command(
        ['dcos', 'package', 'install', 'helloworld'] + args,
        stdout=stdout,
        returncode=returncode,
        stdin=stdin)


def _uninstall_helloworld(
        args=[],
        stdout=b'',
        stderr=b'',
        returncode=0):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld'] + args,
                   stdout=stdout,
                   stderr=stderr,
                   returncode=returncode)


def _uninstall_chronos(args=[], returncode=0, stdout=b'', stderr=''):
    result_returncode, result_stdout, result_stderr = exec_command(
        ['dcos', 'package', 'uninstall', 'chronos'] + args)

    assert result_returncode == returncode
    assert result_stdout == stdout
    assert result_stderr.decode('utf-8').startswith(stderr)


def _install_chronos(
        args=['--yes'],
        returncode=0,
        stdout=b'Installing package [chronos] version [2.3.4]\n',
        stderr=b'',
        preInstallNotes=b'We recommend a minimum of one node with at least 1 '
                        b'CPU and 2GB of RAM available for the Chronos '
                        b'Service.\n',
        postInstallNotes=b'Chronos DCOS Service has been successfully '
                         b'''installed!

\tDocumentation: http://mesos.github.io/chronos
\tIssues: https://github.com/mesos/chronos/issues\n''',
        stdin=None):

    cmd = ['dcos', 'package', 'install', 'chronos'] + args
    assert_command(
        cmd,
        returncode,
        preInstallNotes + stdout + postInstallNotes,
        stderr,
        stdin=stdin)


def _list(args=['--json'],
          stdout=b'[]\n'):
    assert_command(['dcos', 'package', 'list'] + args,
                   stdout=stdout)


def _helloworld():
    stdout = b'''A sample pre-installation message
Installing package [helloworld] version [0.1.0]
Installing CLI subcommand for package [helloworld]
New command available: dcos helloworld
A sample post-installation message
'''
    return _package('helloworld',
                    stdout=stdout)


@contextlib.contextmanager
def _package(name,
             stdout=b''):
    """Context manager that deploys an app on entrance, and removes it on
    exit.

    :param path: path to app's json definition:
    :type path: str
    :param app_id: app id
    :type app_id: str
    :rtype: None
    """

    assert_command(['dcos', 'package', 'install', name, '--yes'],
                   stdout=stdout)
    try:
        yield
    finally:
        assert_command(['dcos', 'package', 'uninstall', name])
