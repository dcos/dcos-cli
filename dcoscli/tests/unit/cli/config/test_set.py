from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_set():
    runner = CliRunner()
    result = runner.invoke(dcos, ['config', 'set'])
    assert result.exit_code == 0
    assert result.output == 'Set a config.\n'
