from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_remove():
    runner = CliRunner()
    result = runner.invoke(dcos, ['config', 'unset'])
    assert result.exit_code == 0
    assert result.output == 'Unset a config.\n'
