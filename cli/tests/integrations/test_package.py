import contextlib
import json
import os
import subprocess
import sys

import pytest
import six

from dcos import config, constants, errors, http, subcommand, util

from dcoscli.test.common import (assert_command, assert_lines, base64_to_dict,
                                 delete_zk_node,
                                 delete_zk_nodes, exec_command,
                                 file_json, update_config)
from dcoscli.test.marathon import watch_all_deployments
from dcoscli.test.package import (setup_universe_server,
                                  teardown_universe_server,
                                  UNIVERSE_REPO, UNIVERSE_TEST_REPOS)
from dcoscli.test.service import get_services, service_shutdown
from ..common import file_bytes


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({constants.PATH_ENV: os.environ[constants.PATH_ENV]})

    return r


def setup_module(module):
    setup_universe_server()


def teardown_module(module):
    services = get_services()
    for framework in services:
        if framework['name'] == 'chronos':
            service_shutdown(framework['id'])

    teardown_universe_server()


@pytest.fixture(scope="module")
def zk_znode(request):
    request.addfinalizer(delete_zk_nodes)
    return request


def test_package():
    with open('dcoscli/data/help/package.txt') as content:
        assert_command(['dcos', 'package', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    info = b"Install and manage DC/OS software packages\n"
    assert_command(['dcos', 'package', '--info'],
                   stdout=info)


def test_version():
    assert_command(['dcos', 'package', '--version'],
                   stdout=b'dcos-package version SNAPSHOT\n')


def test_repo_list():
    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "helloworld-universe: {helloworld-universe}\n"
        ).format(**UNIVERSE_TEST_REPOS),
        'utf-8'
    )

    assert_command(['dcos', 'package', 'repo', 'list'], stdout=repo_list)

    # test again, but override the dcos_url with a cosmos_url config
    dcos_url = config.get_config_val("core.dcos_url")
    with update_config('package.cosmos_url', dcos_url):
        assert_command(['dcos', 'package', 'repo', 'list'], stdout=repo_list)


def test_repo_add_and_remove():
    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "helloworld-universe: {helloworld-universe}\n"
            "Universe: {0}\n"
        ).format(UNIVERSE_REPO, **UNIVERSE_TEST_REPOS),
        'utf-8'
    )

    args = ["Universe", UNIVERSE_REPO]
    _repo_add(args, repo_list)

    repo17 = "https://universe.mesosphere.com/repo-1.7"
    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "1.7-universe: {0}\n"
            "helloworld-universe: {helloworld-universe}\n"
            "Universe: {1}\n"
        ).format(repo17,  UNIVERSE_REPO, **UNIVERSE_TEST_REPOS),
        'utf-8'
    )

    args = ["1.7-universe", repo17, '--index=1']
    _repo_add(args, repo_list)

    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "helloworld-universe: {helloworld-universe}\n"
            "Universe: {0}\n"
        ).format(UNIVERSE_REPO, **UNIVERSE_TEST_REPOS),
        'utf-8'
    )
    _repo_remove(['1.7-universe'], repo_list)

    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "helloworld-universe: {helloworld-universe}\n"
        ).format(**UNIVERSE_TEST_REPOS),
        'utf-8'
    )
    _repo_remove(['Universe'], repo_list)


def test_repo_remove_multi():
    # Add "Universe" repo so we can test removing it
    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "helloworld-universe: {helloworld-universe}\n"
            "Universe: {0}\n"
        ).format(UNIVERSE_REPO, **UNIVERSE_TEST_REPOS),
        'utf-8'
    )
    args = ["Universe", UNIVERSE_REPO]
    _repo_add(args, repo_list)

    # Add "1.7-universe" repo so we can test removing it
    repo17 = "https://universe.mesosphere.com/repo-1.7"
    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "1.7-universe: {1}\n"
            "helloworld-universe: {helloworld-universe}\n"
            "Universe: {0}\n"
        ).format(UNIVERSE_REPO, repo17, **UNIVERSE_TEST_REPOS),
        'utf-8'
    )
    args = ["1.7-universe", repo17, '--index=1']
    _repo_add(args, repo_list)

    repo_list = bytes(
        (
            "test-universe: {test-universe}\n"
            "helloworld-universe: {helloworld-universe}\n"
        ).format(**UNIVERSE_TEST_REPOS),
        'utf-8'
    )
    _repo_remove(['1.7-universe', 'Universe'], repo_list)


def test_repo_empty():
    for name in UNIVERSE_TEST_REPOS.keys():
        assert_command(['dcos', 'package', 'repo', 'remove', name])

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'repo', 'list'])
    stderr_msg = (b"There are currently no repos configured. "
                  b"Please use `dcos package repo add` to add a repo\n")
    assert returncode == 1
    assert stdout == b''
    assert stderr == stderr_msg

    for name, url in UNIVERSE_TEST_REPOS.items():
        assert_command(['dcos', 'package', 'repo', 'add', name, url])


def test_describe_nonexistent():
    assert_command(['dcos', 'package', 'describe', 'xyzzy'],
                   stderr=b'Package [xyzzy] not found\n',
                   returncode=1)


def test_describe_nonexistent_version():
    stderr = b'Version [a.b.c] of package [helloworld] not found\n'
    assert_command(['dcos', 'package', 'describe', 'helloworld',
                    '--package-version=a.b.c'],
                   stderr=stderr,
                   returncode=1)


def test_describe_cli():
    stdout = file_json(
        'tests/data/package/json/test_describe_cli_helloworld.json')
    assert_command(['dcos', 'package', 'describe', 'helloworld', '--cli'],
                   stdout=stdout)


def test_describe_app():
    stdout = file_bytes(
        'tests/data/package/json/test_describe_app_helloworld.json')
    assert_command(['dcos', 'package', 'describe', 'helloworld', '--app'],
                   stdout=stdout)


def test_describe_config():
    stdout = file_json(
        'tests/data/package/json/test_describe_helloworld_config.json')
    assert_command(['dcos', 'package', 'describe', 'helloworld', '--config'],
                   stdout=stdout)


def test_describe_render():
    stdout = file_json(
        'tests/data/package/json/test_describe_helloworld_app_render.json')
    stdout = json.loads(stdout.decode('utf-8'))
    expected_labels = stdout.pop("labels", None)

    returncode, stdout_, stderr = exec_command(
        ['dcos', 'package', 'describe', 'helloworld', '--app', '--render'])

    stdout_ = json.loads(stdout_.decode('utf-8'))
    actual_labels = stdout_.pop("labels", None)

    for label, value in expected_labels.items():
        assert value == actual_labels.get(label)

    assert stdout == stdout_
    assert stderr == b''
    assert returncode == 0


def test_describe_package_version():
    stdout = file_json(
        'tests/data/package/json/test_describe_helloworld.json')

    returncode_, stdout_, stderr_ = exec_command(
        ['dcos', 'package', 'describe', 'helloworld',
            '--package-version=0.1.0'])

    assert returncode_ == 0
    output = json.loads(stdout_.decode('utf-8'))
    assert output == json.loads(stdout.decode('utf-8'))
    assert stderr_ == b''


def test_describe_package_versions():
    stdout = file_bytes(
        'tests/data/package/json/test_describe_helloworld_versions.json')
    assert_command(
        ['dcos', 'package', 'describe', 'helloworld', '--package-versions'],
        stdout=stdout)


def test_describe_options():
    stdout = file_json(
        'tests/data/package/json/test_describe_app_options.json')
    stdout = json.loads(stdout.decode('utf-8'))
    expected_labels = stdout.pop("labels", None)

    with util.temptext(b'{"name": "hallo", "port": 80}') as options:
        returncode, stdout_, stderr = exec_command(
            ['dcos', 'package', 'describe', '--app', '--options',
             options[1], 'helloworld'])

    stdout_ = json.loads(stdout_.decode('utf-8'))
    actual_labels = stdout_.pop("labels", None)

    for label, value in expected_labels.items():
        if label in ["DCOS_PACKAGE_OPTIONS"]:
            # We covert the metadata into a dictionary
            # so that failures in equality are more descriptive
            assert base64_to_dict(value) == \
                base64_to_dict(actual_labels.get(label))
        else:
            assert value == actual_labels.get(label)

    assert stdout == stdout_
    assert stderr == b''
    assert returncode == 0


def test_describe_app_cli():
    stdout = file_bytes(
        'tests/data/package/json/test_describe_app_cli.json')
    assert_command(
        ['dcos', 'package', 'describe', 'helloworld', '--app', '--cli'],
        stdout=stdout)


def test_bad_install():
    stderr = """\
Please create a JSON file with the appropriate options, and pass the \
/path/to/file as an --options argument.
"""
    with util.temptext(b'{"nom": "hallo"}') as options:
        args = ['--options='+options[1], '--yes']
        _install_bad_helloworld(args=args, stderr=stderr)


def test_bad_install_helloworld_msg():
    terms_conditions = (
        b'By Deploying, you agree to the Terms '
        b'and Conditions https://mesosphere.com/'
        b'catalog-terms-conditions/#community-services\n'
        b'A sample pre-installation message\n'
        b'Installing Marathon app for package [helloworld] version '
        b'[0.1.0]\n'
    )

    stdout = (
        terms_conditions +
        b'Installing CLI subcommand for package [helloworld] '
        b'version [0.1.0]\n'
        b'New command available: dcos ' +
        _executable_name(b'helloworld') +
        b'\nA sample post-installation message\n'
    )

    with util.temptext(b'{"name": "/foo"}') as foo, \
            util.temptext(b'{"name": "/foo/bar"}') as foobar:

        _install_helloworld(['--yes', '--options='+foo[1]], stdout=stdout)

        stderr = (b'Object is not valid\n'
                  b'Groups and Applications may not have the same '
                  b'identifier.\n')

        _install_helloworld(['--yes', '--options='+foobar[1]],
                            stdout=terms_conditions,
                            stderr=stderr,
                            returncode=1)
        _uninstall_helloworld()


def test_uninstall_cli_only_when_no_apps_remain():
    with util.temptext(b'{"name": "/hello1"}') as opts_hello1, \
         util.temptext(b'{"name": "/hello2"}') as opts_hello2:

        stdout = (
            b'By Deploying, you agree to the Terms '
            b'and Conditions https://mesosphere.com/'
            b'catalog-terms-conditions/#community-services\n'
            b'A sample pre-installation message\n'
            b'Installing Marathon app for package [helloworld] version '
            b'[0.1.0]\n'
            b'Installing CLI subcommand for package [helloworld] '
            b'version [0.1.0]\n'
            b'New command available: dcos ' +
            _executable_name(b'helloworld') +
            b'\nA sample post-installation message\n'
        )

        stderr = b'Uninstalled package [helloworld] version [0.1.0]\n'
        with _package(name='helloworld',
                      args=['--yes', '--options='+opts_hello1[1]],
                      stdout=stdout,
                      uninstall_app_id='/hello1',
                      uninstall_stderr=stderr):

            with _package(name='helloworld',
                          args=['--yes', '--options='+opts_hello2[1]],
                          stdout=stdout,
                          uninstall_app_id='/hello2',
                          uninstall_stderr=stderr):

                subcommand.command_executables('helloworld')

            # helloworld subcommand should still be there as there is the
            # /hello1 app installed
            subcommand.command_executables('helloworld')

        # helloworld subcommand should have been removed
        with pytest.raises(errors.DCOSException) as exc_info:
            subcommand.command_executables('helloworld')

        assert str(exc_info.value) == "'helloworld' is not a dcos command."


def test_install_missing_options_file():
    """Test that a missing options file results in the expected stderr
    message."""
    assert_command(
        ['dcos', 'package', 'install', 'helloworld', '--yes',
         '--options=asdf.json'],
        returncode=1,
        stderr=b"Error opening file [asdf.json]: No such file or directory\n")


def test_install_specific_version():
    stdout = (
        b'By Deploying, you agree to the Terms and Conditions https://'
        b'mesosphere.com/catalog-terms-conditions/#community-services\n'
        b'A sample pre-installation message\n'
        b'Installing Marathon app for package [helloworld] version [0.1.0]\n'
        b'Installing CLI subcommand for package [helloworld] version [0.1.0]\n'
        b'New command available: dcos ' +
        _executable_name(b'helloworld') +
        b'\nA sample post-installation message\n'
    )

    uninstall_stderr = b'Uninstalled package [helloworld] version [0.1.0]\n'

    with _package(name='helloworld',
                  args=['--yes', '--package-version=0.1.0'],
                  stdout=stdout,
                  uninstall_stderr=uninstall_stderr):

        returncode, stdout, stderr = exec_command(
            ['dcos', 'package', 'list', 'helloworld', '--json'])
        assert returncode == 0
        assert stderr == b''
        assert json.loads(stdout.decode('utf-8'))[0]['version'] == "0.1.0"


def test_install_bad_package_version():
    stderr = b'Version [a.b.c] of package [cassandra] not found\n'
    assert_command(
        ['dcos', 'package', 'install', 'cassandra',
         '--package-version=a.b.c'],
        returncode=1,
        stderr=stderr)


def test_install_noninteractive():
    returncode, stdout, _ = exec_command(
        ['dcos', 'package', 'install', 'hello-world'],
        timeout=30,
        stdin=subprocess.DEVNULL)

    assert returncode == 1
    assert b"'' is not a valid response" in stdout


def test_package_metadata():
    _install_helloworld()

    # test marathon labels
    expected_source = bytes(
        UNIVERSE_TEST_REPOS['helloworld-universe'],
        'utf-8'
    )

    expected_labels = {
        'DCOS_PACKAGE_NAME': b'helloworld',
        'DCOS_PACKAGE_VERSION': b'0.1.0',
        'DCOS_PACKAGE_SOURCE': expected_source,
    }

    app_labels = _get_app_labels('helloworld')
    for label, value in expected_labels.items():
        assert value == six.b(app_labels.get(label))

    # test local package.json
    package = file_json(
        'tests/data/package/json/test_package_metadata.json')
    package = json.loads(package.decode("UTF-8"))

    helloworld_subcommand = subcommand.InstalledSubcommand("helloworld")

    # test local package.json
    assert helloworld_subcommand.package_json() == package

    # uninstall helloworld
    _uninstall_helloworld()


def test_install_missing_package():
    stderr = b'Package [missing-package] not found\n'
    assert_command(['dcos', 'package', 'install', 'missing-package'],
                   returncode=1,
                   stderr=stderr)


def test_uninstall_missing():
    stderr = 'Package [chronos] is not installed\n'
    _uninstall_chronos(returncode=1, stderr=stderr)

    stderr = 'Package [chronos] with id [/chronos-1] is not installed\n'
    _uninstall_chronos(
        args=['--app-id=chronos-1'],
        returncode=1,
        stderr=stderr)


def test_uninstall_subcommand():
    _install_helloworld()
    _uninstall_helloworld()
    _list(args=['--json'], stdout=b'[]\n')


def test_uninstall_cli():
    _install_helloworld()
    _uninstall_cli_helloworld()

    stdout_json = {
        "apps": [
            "/helloworld"
        ],
        "description": "Example DCOS application package",
        "framework": False,
        "maintainer": "support@mesosphere.io",
        "name": "helloworld",
        "packagingVersion": "3.0",
        "postInstallNotes": "A sample post-installation message",
        "preInstallNotes": "A sample pre-installation message",
        "selected": False,
        "tags": [
            "mesosphere",
            "example",
            "subcommand"
        ],
        "version": "0.1.0",
        "website": "https://github.com/mesosphere/dcos-helloworld"
    }

    returncode_, stdout_, stderr_ = exec_command(
        ['dcos', 'package', 'list', '--json'])
    assert stderr_ == b''
    assert returncode_ == 0
    output = json.loads(stdout_.decode('utf-8'))[0]
    assert output == stdout_json
    _uninstall_helloworld()


def test_uninstall_multiple_apps():
    stdout = (
        b'By Deploying, you agree to the Terms '
        b'and Conditions https://mesosphere.com/'
        b'catalog-terms-conditions/#community-services\n'
        b'A sample pre-installation message\n'
        b'Installing Marathon app for package [helloworld] version '
        b'[0.1.0]\n'
        b'A sample post-installation message\n'
    )

    with util.temptext(b'{"name": "/helloworld-1"}') as hello1, \
            util.temptext(b'{"name": "/helloworld-2"}') as hello2:

        _install_helloworld(
            ['--yes', '--options='+hello1[1], '--app'],
            stdout=stdout)

        _install_helloworld(
            ['--yes', '--options='+hello2[1], '--app'],
            stdout=stdout)

        stderr = (b"Multiple apps named [helloworld] are installed: "
                  b"[/helloworld-1, /helloworld-2].\n"
                  b"Please use --app-id to specify the ID of the app "
                  b"to uninstall, or use --all to uninstall all apps.\n")

        _uninstall_helloworld(stderr=stderr, returncode=1, uninstalled=b'')

        _uninstall_helloworld(args=['--all'])


def test_list(zk_znode):
    empty = b'[]\n'

    _list(args=['--json'], stdout=empty)
    _list(args=['xyzzy', '--json'], stdout=empty)
    _list(args=['--app-id=/xyzzy', '--json'], stdout=empty)

    with _chronos_package():

        expected_output = file_json(
            'tests/data/package/json/test_list_chronos.json')
        _list(args=['--json'], stdout=expected_output)
        _list(args=['--json', 'chronos'], stdout=expected_output)
        _list(args=['--json', '--app-id=/chronos'], stdout=expected_output)

    le_package = 'ceci-nest-pas-une-package'
    _list(args=['--json', le_package], stdout=empty)
    _list(args=['--json', '--app-id=/' + le_package], stdout=empty)


def test_list_table():
    with _helloworld():
        assert_lines(['dcos', 'package', 'list'], 2)


def test_install_yes():
    with open('tests/data/package/assume_yes.txt') as yes_file:
        _install_helloworld(
            args=[],
            stdin=yes_file,
            stdout=(
                b'By Deploying, you agree to the Terms '
                b'and Conditions https://mesosphere.com/'
                b'catalog-terms-conditions/#community-services\n'
                b'A sample pre-installation message\n'
                b'Continue installing? [yes/no] '
                b'Installing Marathon app for package [helloworld] version '
                b'[0.1.0]\n'
                b'Installing CLI subcommand for package [helloworld] '
                b'version [0.1.0]\n'
                b'New command available: dcos ' +
                _executable_name(b'helloworld') +
                b'\nA sample post-installation message\n'
            )
        )
        _uninstall_helloworld()


def test_install_no():
    with open('tests/data/package/assume_no.txt') as no_file:
        _install_helloworld(
            args=[],
            stdin=no_file,
            stdout=(
                b'By Deploying, you agree to the Terms '
                b'and Conditions https://mesosphere.com/'
                b'catalog-terms-conditions/#community-services\n'
                b'A sample pre-installation message\n'
                b'Continue installing? [yes/no] Exiting installation.\n'
            ),
            returncode=1
        )


def test_list_cli():
    _install_helloworld()
    stdout = file_json(
        'tests/data/package/json/test_list_helloworld.json')
    _list(args=['--json'], stdout=stdout)
    _uninstall_helloworld()

    stdout = (
        b'By Deploying, you agree to the Terms '
        b'and Conditions https://mesosphere.com/'
        b'catalog-terms-conditions/#community-services\n'
        b"Installing CLI subcommand for package [helloworld] " +
        b"version [0.1.0]\n"
        b"New command available: dcos " +
        _executable_name(b'helloworld') +
        b"\n"
    )
    _install_helloworld(args=['--cli', '--yes'], stdout=stdout)

    stdout = file_json(
        'tests/data/package/json/test_list_helloworld_cli.json')
    _list(args=['--json'], stdout=stdout)

    _uninstall_cli_helloworld()


def test_list_cli_only(env):
    helloworld_path = 'tests/data/package/json/test_list_helloworld_cli.json'
    helloworld_json = file_json(helloworld_path)

    with _helloworld_cli(), \
            update_config('package.cosmos_url', 'http://nohost', env):
        assert_command(
            cmd=['dcos', 'package', 'list', '--json', '--cli'],
            stdout=helloworld_json)

        assert_command(
            cmd=['dcos', 'package', 'list', '--json', '--cli',
                 '--app-id=/helloworld'],
            stdout=b'[]\n')

        assert_command(
            cmd=['dcos', 'package', 'list', '--json', '--cli', 'helloworld'],
            stdout=helloworld_json)


def test_cli_global():
    helloworld_path = 'tests/data/package/json/test_list_helloworld_cli.json'
    helloworld_json = file_json(helloworld_path)

    with _helloworld_cli(global_=True):
        assert os.path.exists(subcommand.global_package_dir("helloworld"))

        assert_command(
            cmd=['dcos', 'package', 'list', '--json', '--cli'],
            stdout=helloworld_json)


def test_uninstall_multiple_frameworknames(zk_znode):
    _install_chronos(
        args=['--yes', '--options=tests/data/package/chronos-1.json'])
    _install_chronos(
        args=['--yes', '--options=tests/data/package/chronos-2.json'])

    watch_all_deployments()

    expected_output = file_json(
        'tests/data/package/json/test_list_chronos_two_users.json')

    _list(args=['--json'], stdout=expected_output)
    _list(args=['--json', 'chronos'], stdout=expected_output)
    _list(args=['--json', '--app-id=/chronos-user-1'], stdout=file_json(
        'tests/data/package/json/test_list_chronos_user_1.json'))

    _list(args=['--json', '--app-id=/chronos-user-2'], stdout=file_json(
        'tests/data/package/json/test_list_chronos_user_2.json'))

    _uninstall_chronos(
        args=['--app-id=chronos-user-1'],
        returncode=1,
        stderr='Uninstalled package [chronos] version [2.5.0-1]\n'
               'Unable to shutdown [chronos] service framework with name '
               '[chronos-user] because there are multiple framework ids '
               'matching this name: ')

    _uninstall_chronos(
        args=['--app-id=chronos-user-2'],
        returncode=1,
        stderr='Uninstalled package [chronos] version [2.5.0-1]\n'
               'Unable to shutdown [chronos] service framework with name '
               '[chronos-user] because there are multiple framework ids '
               'matching this name: ')

    for framework in get_services(args=['--inactive']):
        if framework['name'] == 'chronos-user':
            service_shutdown(framework['id'])


def test_search():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', 'cron', '--json'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert stderr == b''

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', 'xyzzy', '--json'])

    assert returncode == 0
    assert b'"packages": []' in stdout
    assert stderr == b''

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', 'xyzzy'])

    assert returncode == 1
    assert b'' == stdout
    assert stderr == b'No packages found.\n'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', '--json'])

    registries = json.loads(stdout.decode('utf-8'))
    # assert the number of packages is gte the number at the time
    # this test was written
    assert len(registries['packages']) >= 5

    assert returncode == 0
    assert stderr == b''


def test_search_table():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert len(stdout.decode('utf-8').split('\n')) > 5
    assert stderr == b''


def test_search_ends_with_wildcard():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', 'c*', '--json'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert b'cassandra' in stdout
    assert stderr == b''

    registries = json.loads(stdout.decode('utf-8'))
    # cosmos matches wildcards in name/description/tags
    # so will find more results (3 instead of 2)
    assert len(registries['packages']) >= 2


def test_search_start_with_wildcard():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', '*nos', '--json'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert stderr == b''

    registries = json.loads(stdout.decode('utf-8'))
    assert len(registries['packages']) == 1


def test_search_middle_with_wildcard():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'search', 'c*s', '--json'])

    assert returncode == 0
    assert b'chronos' in stdout
    assert stderr == b''

    registries = json.loads(stdout.decode('utf-8'))
    assert len(registries['packages']) == 5


def _get_app_labels(app_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show', app_id])

    assert returncode == 0
    assert stderr == b''

    app_json = json.loads(stdout.decode('utf-8'))
    return app_json.get('labels')


def _executable_name(name):
    if sys.platform == 'win32':
        return name + b'.exe'
    else:
        return name


def _install_helloworld(
        args=['--yes'],
        stdout=(
            b'By Deploying, you agree to the Terms '
            b'and Conditions https://mesosphere.com/'
            b'catalog-terms-conditions/#community-services\n'
            b'A sample pre-installation message\n'
            b'Installing Marathon app for package [helloworld] '
            b'version [0.1.0]\n'
            b'Installing CLI subcommand for package [helloworld] '
            b'version [0.1.0]\n'
            b'New command available: dcos ' +
            _executable_name(b'helloworld') +
            b'\nA sample post-installation message\n'
        ),
        stderr=b'',
        returncode=0,
        stdin=None):
    assert_command(
        ['dcos', 'package', 'install', 'helloworld'] + args,
        stdout=stdout,
        returncode=returncode,
        stdin=stdin,
        stderr=stderr)


def _uninstall_helloworld(
        args=[],
        stdout=b'',
        stderr=b'',
        returncode=0,
        uninstalled=b'Uninstalled package [helloworld] version [0.1.0]\n'):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld',
                    '--yes'] + args,
                   stdout=stdout,
                   stderr=uninstalled+stderr,
                   returncode=returncode)

    watch_all_deployments()


def _uninstall_cli_helloworld(
        args=[],
        stdout=b'',
        stderr=b'',
        returncode=0):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld',
                    '--cli'] + args,
                   stdout=stdout,
                   stderr=stderr,
                   returncode=returncode)


def _uninstall_chronos(args=[], returncode=0, stdout=b'', stderr=''):
    result_returncode, result_stdout, result_stderr = exec_command(
        ['dcos', 'package', 'uninstall', 'chronos', '--yes'] + args)

    assert result_returncode == returncode
    assert result_stdout == stdout
    assert result_stderr.decode('utf-8').startswith(stderr)


def _install_bad_helloworld(
        args=['--yes'],
        stdout=(
            b'By Deploying, you agree to the Terms '
            b'and Conditions https://mesosphere.com/'
            b'catalog-terms-conditions/#community-services\n'
            b'A sample pre-installation message\n'
        ),
        stderr=''):
    cmd = ['dcos', 'package', 'install', 'helloworld'] + args
    returncode_, stdout_, stderr_ = exec_command(cmd)
    assert returncode_ == 1
    assert stderr in stderr_.decode('utf-8')
    assert stdout_ == stdout


def _install_chronos(
        args=['--yes'],
        returncode=0,
        stdout=b'Installing Marathon app for package [chronos] '
               b'version [2.5.0-1]\n',
        stderr=b'',
        pre_install_notes=(
            b'By Deploying, you agree to the Terms '
            b'and Conditions https://mesosphere.com/'
            b'catalog-terms-conditions/#certified-services\n'
            b'We recommend a minimum of one node with at least '
            b'1 CPU and 2GB of RAM available for the '
            b'Chronos Service.\n'
        ),
        post_install_notes=b'Chronos DCOS Service has been successfully '
                           b'installed!\n\n'
                           b'\tDocumentation: http://mesos.github.io/'
                           b'chronos\n'
                           b'\tIssues: https://github.com/mesos/chronos/'
                           b'issues\n',
        stdin=None):

    cmd = ['dcos', 'package', 'install', 'chronos'] + args
    assert_command(
        cmd,
        returncode,
        pre_install_notes + stdout + post_install_notes,
        stderr,
        stdin=stdin)


@contextlib.contextmanager
def _chronos_package(
        args=['--yes'],
        returncode=0,
        stdout=b'Installing Marathon app for package [chronos] '
               b'version [2.5.0-1]\n',
        stderr=b'',
        pre_install_notes=(
            b'By Deploying, you agree to the Terms '
            b'and Conditions https://mesosphere.com/'
            b'catalog-terms-conditions/#certified-services\n'
            b'We recommend a minimum of one node with at least '
            b'1 CPU and 2GB of RAM available for the '
            b'Chronos Service.\n'
        ),
        post_install_notes=b'Chronos DCOS Service has been successfully '
                           b'installed!\n\n'
                           b'\tDocumentation: http://mesos.github.io/'
                           b'chronos\n'
                           b'\tIssues: https://github.com/mesos/chronos/'
                           b'issues\n',
        stdin=None):

    _install_chronos(
        args,
        returncode,
        stdout,
        stderr,
        pre_install_notes,
        post_install_notes,
        stdin)
    try:
        yield
    finally:
        _uninstall_chronos()
        delete_zk_node('chronos')
        watch_all_deployments()


def _list(args, stdout):
    assert_command(['dcos', 'package', 'list'] + args, stdout=stdout)


HELLOWORLD_CLI_STDOUT = (
    b'Installing CLI subcommand for package [helloworld] '
    b'version [0.1.0]\n'
    b'New command available: dcos ' +
    _executable_name(b'helloworld') + b'\n'
)


def _helloworld():
    stdout = (
        b'By Deploying, you agree to the Terms '
        b'and Conditions https://mesosphere.com/'
        b'catalog-terms-conditions/#community-services\n'
        b'A sample pre-installation message\n'
        b'Installing Marathon app for package [helloworld] version '
        b'[0.1.0]\n' + HELLOWORLD_CLI_STDOUT +
        b'A sample post-installation message\n'
    )

    stderr = b'Uninstalled package [helloworld] version [0.1.0]\n'
    return _package(name='helloworld',
                    args=['--yes'],
                    stdout=stdout,
                    uninstall_stderr=stderr)


def _helloworld_cli(global_=False):
    args = ['--yes', '--cli']
    if global_:
        args += ['--global']
    return _package(name='helloworld',
                    args=args,
                    stdout=(
                        b'By Deploying, you agree to the Terms '
                        b'and Conditions https://mesosphere.com/'
                        b'catalog-terms-conditions/#community-services\n' +
                        HELLOWORLD_CLI_STDOUT
                    ),
                    uninstall_stderr=b'')


@contextlib.contextmanager
def _package(name,
             args,
             stdout=b'',
             uninstall_confirmation=True,
             uninstall_app_id='',
             uninstall_stderr=b''):
    """Context manager that installs a package on entrance, and uninstalls it on
    exit.

    :param name: package name
    :type name: str
    :param args: extra CLI args
    :type args: [str]
    :param stdout: Expected stdout
    :type stdout: bytes
    :param uninstall_app_id: App id for uninstallation
    :type uninstall_app_id: string
    :param uninstall_stderr: Expected stderr
    :type uninstall_stderr: bytes
    :rtype: None
    """

    command = ['dcos', 'package', 'install', name] + args

    installed = False
    timeout = http.DEFAULT_READ_TIMEOUT
    try:
        returncode_, stdout_, _ = exec_command(command, timeout=timeout)
        installed = (returncode_ == 0)

        assert installed
        assert stdout_ == stdout

        yield
    finally:
        if installed:
            command = ['dcos', 'package', 'uninstall', name]
            if uninstall_confirmation:
                command.append('--yes')
            if uninstall_app_id:
                command.append('--app-id='+uninstall_app_id)
            assert_command(command, stderr=uninstall_stderr)
            watch_all_deployments()


def _repo_add(args=[], repo_list=[]):
    assert_command(['dcos', 'package', 'repo', 'add'] + args)
    assert_command(['dcos', 'package', 'repo', 'list'], stdout=repo_list)


def _repo_remove(args=[], repo_list=[]):
    assert_command(['dcos', 'package', 'repo', 'remove'] + args)
    assert_command(['dcos', 'package', 'repo', 'list'], stdout=repo_list)
