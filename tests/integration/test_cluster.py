import json

from .common import exec_cmd, default_cluster, default_cluster_with_plugins  # noqa: F401


def test_cluster_list(default_cluster):
    code, out, err = exec_cmd(['dcos', 'cluster', 'list'])
    assert code == 0
    assert err == ''

    lines = out.splitlines()
    assert len(lines) == 2

    # heading
    assert lines[0].split() == ['NAME', 'ID', 'STATUS', 'VERSION', 'URL']

    # cluster item
    cluster_item = lines[1].split()
    assert cluster_item[0] == '*'
    assert cluster_item[3] == 'AVAILABLE'
    assert cluster_item[5] == default_cluster['dcos_url']


def test_cluster_list_json(default_cluster):
    code, out, err = exec_cmd(['dcos', 'cluster', 'list', '--json'])
    assert code == 0
    assert err == ''

    out = json.loads(out)
    assert len(out) == 1
    assert out[0]['status'] == 'AVAILABLE'
    assert out[0]['url'] == default_cluster['dcos_url']


def test_empty_cluster_list():
    code, out, err = exec_cmd(['dcos', 'cluster', 'list', '--json'])
    assert code == 0
    assert err == ''
    assert out == '[]\n'


def test_cluster_setup_non_superuser(default_cluster_with_plugins):
    username='nonsuperuser'
    password='nonsuperpassword'
    exec_cmd(['dcos', 'security', 'org', 'users',
              'create', username, '--password={}'.format(password)])
    # No assert against the output because this will either return 0 if the user doesn't exist or
    # 1 if the user already exists but we don't have an easy way to check the exact error to
    # ensure it was "good" failure

    code, out, err = exec_cmd(['dcos', 'cluster', 'setup', default_cluster_with_plugins['dcos_url'],
                               '--username={}'.format(username),
                               '--password={}'.format(password)])
    assert code == 0
