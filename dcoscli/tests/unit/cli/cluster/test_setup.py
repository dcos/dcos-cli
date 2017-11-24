from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_setup():
    runner = CliRunner()
    result = runner.invoke(dcos, ['cluster', 'setup'])
    assert result.exit_code == 0
    assert result.output == 'Setup a cluster.\n'
