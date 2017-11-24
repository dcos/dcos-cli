from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_attach():
    runner = CliRunner()
    result = runner.invoke(dcos, ['cluster', 'attach'])
    assert result.exit_code == 0
    assert result.output == 'Attach to a cluster.\n'
