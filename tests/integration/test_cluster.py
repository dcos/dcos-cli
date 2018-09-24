import json
import os

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
    username = 'nonsuperuser'
    password = 'nonsuperpassword'

    # Ignore the exit code as it's not an idempotent operation and our integration
    # tests on different platforms share the same cluster concurrently.
    exec_cmd(['dcos', 'security', 'org', 'users',
              'create', username, '--password', password])

    code, out, err = exec_cmd(['dcos', 'cluster', 'setup', default_cluster_with_plugins['dcos_url'],
                               '--username', username, '--password', password])
    assert code == 0
    assert out == ""
    assert err == ('In order to install the "dcos-enterprise-cli" plugin, '
                   'make sure your user has the "dcos:adminrouter:package" '
                   'permission and run "dcos package install dcos-enterprise-cli".\n')


def test_cluster_setup_with_acs_token_env(default_cluster):
    code, out, _ = exec_cmd(['dcos', 'config', 'show', 'core.dcos_acs_token'])
    assert code == 0

    env = os.environ.copy()
    env['DCOS_CLUSTER_SETUP_ACS_TOKEN'] = out.rstrip()

    code, out, err = exec_cmd(['dcos', 'cluster', 'setup', default_cluster['dcos_url']], env=env)
    assert code == 0
    assert out == ""
    assert err == ""

    code, out, _ = exec_cmd(['dcos', 'config', 'show', 'core.dcos_acs_token'])
    assert code == 0
    assert out.rstrip() == env['DCOS_CLUSTER_SETUP_ACS_TOKEN']
