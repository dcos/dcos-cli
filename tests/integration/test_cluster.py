import json
import os

from .common import setup_cluster, exec_cmd, default_cluster  # noqa: F401


def test_cluster_help():
    code, out, err = exec_cmd(['dcos', 'cluster'])
    assert code == 0
    assert err == ''
    assert out == '''Manage your DC/OS clusters

Usage:
  dcos cluster [command]

Commands:
  attach
      Attach the CLI to a cluster
  link
      Link the current cluster to another one
  list
      List the clusters configured and the ones linked to the current cluster
  remove
      Remove a configured cluster from the CLI
  rename
      Rename a configured cluster
  setup
      Set up the CLI to communicate with a cluster
  unlink
      Unlink the current cluster with one of its linked clusters

Options:
  -h, --help   help for cluster

Use "dcos cluster [command] --help" for more information about a command.
'''


def test_cluster_invalid_usage():
    code, out, err = exec_cmd(['dcos', 'cluster', 'not-a-command'])
    assert code != 0
    assert out == ''
    assert err == '''Usage:
  dcos cluster [command]

Commands:
  attach
      Attach the CLI to a cluster
  link
      Link the current cluster to another one
  list
      List the clusters configured and the ones linked to the current cluster
  remove
      Remove a configured cluster from the CLI
  rename
      Rename a configured cluster
  setup
      Set up the CLI to communicate with a cluster
  unlink
      Unlink the current cluster with one of its linked clusters

Options:
  -h, --help   help for cluster

Use "dcos cluster [command] --help" for more information about a command.

Error: unknown command not-a-command
'''


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


def test_cluster_setup_bundled_core_plugin_strict_mode():
    env = {**os.environ.copy(), **{
        'DCOS_CLUSTER_SETUP_SKIP_CANONICAL_URL_INSTALL': '1',
        'DCOS_CLUSTER_SETUP_SKIP_COSMOS_INSTALL': '1',
        'DCOS_CLI_STRICT_DEPRECATIONS': '1',
    }}

    cmd = 'dcos cluster setup --username={} --password={} http://{}'.format(
        os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_USERNAME'),
        os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_PASSWORD'),
        os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_HOST'))

    code, out, err = exec_cmd(cmd.split(' '), env=env)

    assert code != 0
    assert out == ""
    assert err == ("Extracting \"dcos-core-cli\"...\n"
                   "This setup is deprecated, see "
                   "https://docs.mesosphere.com/1.13/cli/plugins/ "
                   "for more information.\n"
                   "Error: usage of deprecated feature\n")
