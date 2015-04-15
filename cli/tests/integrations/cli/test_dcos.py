import json
import os

import analytics
import dcoscli
from dcos.api import config, constants, util
from dcoscli.main import main

import mock
from common import exec_command
from mock import Mock, patch


def test_default():
    dcos_path = os.path.dirname(os.path.dirname(util.which('dcos')))
    returncode, stdout, stderr = exec_command(['dcos'])

    assert returncode == 0
    assert stdout == """\
Command line utility for the Mesosphere Datacenter Operating
System (DCOS). The Mesosphere DCOS is a distributed operating
system built around Apache Mesos. This utility provides tools
for easy management of a DCOS installation.

Available DCOS commands in '{}':

\tconfig         \tGet and set DCOS command line options
\thelp           \tDisplay command line usage information
\tmarathon       \tDeploy and manage applications on the DCOS
\tpackage        \tInstall and manage DCOS software packages
\tsubcommand     \tInstall and manage DCOS CLI subcommands

Get detailed command description with 'dcos <command> --help'.
""".format(dcos_path).encode('utf-8')
    assert stderr == b''


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos [options] [<command>] [<args>...]

Options:
    --help                      Show this screen
    --version                   Show version
    --log-level=<log-level>     If set then print supplementary messages to
                                stderr at or above this level. The severity
                                levels in the order of severity are: debug,
                                info, warning, error, and critical. E.g.
                                Setting the option to warning will print
                                warning, error and critical messages to stderr.
                                Note: that this does not affect the output sent
                                to stdout by the command.

Environment Variables:
    DCOS_LOG_LEVEL              If set then it specifies that message should be
                                printed to stderr at or above this level. See
                                the --log-level option for details.

    DCOS_CONFIG                 This environment variable points to the
                                location of the DCOS configuration file.

'dcos help' lists all available subcommands. See 'dcos <command> --help'
to read about a specific subcommand.
"""
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', '--version'])

    assert returncode == 0
    assert stdout == b'dcos version 0.1.0\n'
    assert stderr == b''


def test_missing_dcos_config():
    env = {
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_CONFIG' must be set "
                      b"to the DCOS config file.\n")
    assert stderr == b''


def test_dcos_config_not_a_file():
    env = {
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        'DCOS_CONFIG': 'missing/file',
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_CONFIG' maps to "
                      b"'missing/file' and it is not a file.\n")
    assert stderr == b''


def test_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=info', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS command line options\n"


def test_capital_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=INFO', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS command line options\n"


def test_invalid_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=blah', 'config', '--info'])

    assert returncode == 1
    assert stdout == (b"Log level set to an unknown value 'blah'. Valid "
                      b"values are ['debug', 'info', 'warning', 'error', "
                      b"'critical']\n")
    assert stderr == b''


def _mock_analytics_run(args):
    with mock.patch('sys.argv', args):
        analytics.track = Mock()
        analytics.flush = Mock()
        return main()


def _analytics_base_properties(args):
    conf = config.load_from_path(os.environ[constants.DCOS_CONFIG_ENV])
    return {'cmd': ' '.join(args),
            'exit_code': 0,
            'err': None,
            'dcoscli.version': dcoscli.version,
            'config': json.dumps(list(conf.property_items()))}


def test_analytics_no_err():
    args = ['dcos']
    exit_code = _mock_analytics_run(args)

    props = _analytics_base_properties(args)
    analytics.track.assert_called_with('<dcos-cli-user>', 'dcos-cli', props)
    analytics.flush.assert_called_with()
    assert exit_code == 0


def test_analytics_err():
    args = ['dcos', 'marathon', 'task', 'show', 'asdf']
    exit_code = _mock_analytics_run(args)

    props = _analytics_base_properties(args)
    props['exit_code'] = 1
    props['err'] = "Task 'asdf' does not exist\n"
    analytics.track.assert_called_with('<dcos-cli-user>', 'dcos-cli', props)
    analytics.flush.assert_called_with()
    assert exit_code == 1


def test_analytics_report_config():
    args = ['dcos']
    new_env = {constants.DCOS_CONFIG_ENV:
               os.path.join('tests', 'data', 'dcos', 'dcos_no_reporting.toml')}
    with patch.dict(os.environ, new_env):
        exit_code = _mock_analytics_run(args)
        assert analytics.track.call_count == 0
        assert analytics.flush.call_count == 0
        assert exit_code == 0
