from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_logout():
    runner = CliRunner()
    result = runner.invoke(dcos, ['auth', 'logout'])
    assert result.exit_code == 0
    assert result.output == 'Logout of your DC/OS cluster.\n'
