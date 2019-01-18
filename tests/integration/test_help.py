from .common import exec_cmd, default_cluster, default_cluster_with_plugins  # noqa: F401


def test_dcos_help():
    code, out, err = exec_cmd(['dcos'])
    assert code == 0
    assert err == ''
    assert out == '''Usage:
  dcos [command]

Commands:
  auth
      Authenticate to DC/OS cluster
  cluster
      Manage your DC/OS clusters
  config
      Manage the DC/OS configuration file
  help
      Help about any command
  plugin
      Manage CLI plugins

Options:
  --version
      Print version information
  -v, -vv
      Output verbosity (verbose or very verbose)
  -h, --help
      Show usage help

Use "dcos [command] --help" for more information about a command.
'''


def test_dcos_help_with_default_plugins(default_cluster_with_plugins):
    code, out, err = exec_cmd(['dcos'])
    assert code == 0
    assert err == ''
    assert out == '''Usage:
  dcos [command]

Commands:
  auth
      Authenticate to DC/OS cluster
  backup
      Access DC/OS backup functionality
  cluster
      Manage your DC/OS clusters
  config
      Manage the DC/OS configuration file
  help
      Help about any command
  job
      Deploy and manage jobs in DC/OS
  license
      Manage your DC/OS licenses
  marathon
      Deploy and manage applications to DC/OS
  node
      View DC/OS node information
  package
      Install and manage DC/OS software packages
  plugin
      Manage CLI plugins
  security
      DC/OS security related commands
  service
      Manage DC/OS services
  task
      Manage DC/OS tasks

Options:
  --version
      Print version information
  -v, -vv
      Output verbosity (verbose or very verbose)
  -h, --help
      Show usage help

Use "dcos [command] --help" for more information about a command.
'''
