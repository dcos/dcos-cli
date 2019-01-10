from .common import exec_cmd, default_cluster  # noqa: F401


def test_auth_login(default_cluster):
    code, out, err = exec_cmd(
        ['dcos', 'auth', 'login',
         '--username', default_cluster['username'],
         '--password', default_cluster['password']])

    assert code == 0
    assert out == ''
    assert err == ''
