from click.testing import CliRunner

from dcos_cli import __version__
from dcos_cli.cli.dcos import dcos


def test_help():
    runner = CliRunner()
    expected_help_output = """Usage: dcos [OPTIONS] COMMAND [ARGS]...

  Run the dcos command.

Options:
  --debug    Enable debug mode.
  --version  Print version information.
  --help     Show this message and exit.

Commands:
  cluster  Manage your DC/OS clusters.
  config   Manage the DC/OS configuration file.
"""

    result = runner.invoke(dcos)
    assert result.exit_code == 0
    assert result.output == expected_help_output

    result = runner.invoke(dcos, ['--help'])
    assert result.exit_code == 0
    assert result.output == expected_help_output


def test_version():
    runner = CliRunner()
    result = runner.invoke(dcos, ['--version'])
    assert result.exit_code == 0
    assert result.output == __version__ + '\n'


def test_unexisting_command():
    runner = CliRunner()
    result = runner.invoke(dcos, ['make_coffee'])
    assert result.exit_code != 0
