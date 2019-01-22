import json
import os

from .common import setup_cluster, exec_cmd, default_cluster  # noqa: F401


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


def test_cluster_setup_non_superuser(default_cluster):
    username = 'nonsuperuser'
    password = 'nonsuperpassword'

    # Ignore the exit code as it's not an idempotent operation and our integration
    # tests on different platforms share the same cluster concurrently.
    exec_cmd(['dcos', 'security', 'org', 'users',
              'create', username, '--password', password])

    code, out, err = exec_cmd(['dcos', 'cluster', 'setup', default_cluster['dcos_url'],
                               '--username', username, '--password', password])
    assert code == 0
    assert out == ""


def test_cluster_setup_with_acs_token_env(default_cluster):
    env = os.environ.copy()
    env['DCOS_CLUSTER_SETUP_ACS_TOKEN'] = default_cluster['acs_token']

    code, out, err = exec_cmd(['dcos', 'cluster', 'setup', default_cluster['dcos_url']], env=env)
    assert code == 0
    assert out == ""

    code, out, _ = exec_cmd(['dcos', 'config', 'show', 'core.dcos_acs_token'])
    assert code == 0
    assert out.rstrip() == env['DCOS_CLUSTER_SETUP_ACS_TOKEN']


def test_cluster_setup_insecure():
    with setup_cluster(scheme='https', insecure=True):
        code, out, _ = exec_cmd(['dcos', 'config', 'show', 'core.ssl_verify'])
        assert code == 0
        assert out.rstrip() == "false"


def test_cluster_setup_cosmos_plugins():
    env = {'DCOS_CLUSTER_SETUP_SKIP_CANONICAL_URL_INSTALL': '1'}
    with setup_cluster(scheme='https', insecure=True, env=env):
        code, out, err = exec_cmd(['dcos', 'plugin', 'list', '--json'])
        assert code == 0

        plugins = json.loads(out)

        assert len(plugins) == 2
        assert plugins[0]['name'] == 'dcos-core-cli'
        assert plugins[1]['name'] == 'dcos-enterprise-cli'


def test_cluster_setup_bundled_core_plugin():
    env = {
        'DCOS_CLUSTER_SETUP_SKIP_CANONICAL_URL_INSTALL': '1',
        'DCOS_CLUSTER_SETUP_SKIP_COSMOS_INSTALL': '1',
    }
    with setup_cluster(scheme='https', insecure=True, env=env):
        code, out, err = exec_cmd(['dcos', 'plugin', 'list', '--json'])
        assert code == 0

        plugins = json.loads(out)

        assert len(plugins) == 1
        assert plugins[0]['name'] == 'dcos-core-cli'
