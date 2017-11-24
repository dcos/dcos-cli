from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_remove():
    runner = CliRunner()
    result = runner.invoke(dcos, ['cluster', 'remove'])
    assert result.exit_code == 0
    assert result.output == 'Remove cluster(s).\n'
