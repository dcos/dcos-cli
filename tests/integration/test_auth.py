from .common import exec_cmd, default_cluster  # noqa: F401


def test_auth_help():
    code, out, err = exec_cmd(['dcos', 'auth'])
    assert code == 0
    assert err == ''
    assert out == '''Authenticate to DC/OS cluster

Usage:
    dcos auth [command]

Commands:
    list-providers
        List available login providers for a cluster
    login
        Log in to the current cluster
    logout
        Log out the CLI from the current cluster

Options:
    -h, --help
        help for auth

Use "dcos auth [command] --help" for more information about a command.
'''


def test_auth_invalid_usage():
    code, out, err = exec_cmd(['dcos', 'auth', 'not-a-command'])
    assert code != 0
    assert out == ''
    assert err == '''Usage:
    dcos auth [command]

Commands:
    list-providers
        List available login providers for a cluster
    login
        Log in to the current cluster
    logout
        Log out the CLI from the current cluster

Options:
    -h, --help
        help for auth

Use "dcos auth [command] --help" for more information about a command.

Error: unknown command not-a-command
'''


def test_auth_login(default_cluster):
    code, out, err = exec_cmd(
        ['dcos', 'auth', 'login',
         '--username', default_cluster['username'],
         '--password', default_cluster['password']])

    assert code == 0
    assert out == ''
    assert err == ''
