from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_rename():
    runner = CliRunner()
    result = runner.invoke(dcos, ['cluster', 'rename'])
    assert result.exit_code == 0
    assert result.output == 'Rename a cluster.\n'
