from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_list():
    runner = CliRunner()
    result = runner.invoke(dcos, ['config', 'show'])
    assert result.exit_code == 0
    assert result.output == 'Show a config.\n'
