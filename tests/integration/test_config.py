from .common import exec_cmd


def test_config_help():
    code, out, err = exec_cmd(['dcos', 'config'])
    assert code == 0
    assert err == ''
    assert out == '''Manage the DC/OS configuration file

Usage:
  dcos config [command]

Commands:
  set
      Add or set a property in the configuration file used for the current cluster
  show
      Print the configuration file related to the current cluster
  unset
      Remove a property from the configuration file used for the current cluster

Options:
  -h, --help   help for config

Use "dcos config [command] --help" for more information about a command.
'''


def test_config_invalid_usage():
    code, out, err = exec_cmd(['dcos', 'config', 'not-a-command'])
    assert code != 0
    assert out == ''
    assert err == '''Usage:
  dcos config [command]

Commands:
  set
      Add or set a property in the configuration file used for the current cluster
  show
      Print the configuration file related to the current cluster
  unset
      Remove a property from the configuration file used for the current cluster

Options:
  -h, --help   help for config

Use "dcos config [command] --help" for more information about a command.

Error: unknown command not-a-command
'''
