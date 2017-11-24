from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_login():
    runner = CliRunner()
    result = runner.invoke(dcos, ['auth', 'login'])
    assert result.exit_code == 0
    assert result.output == 'Login to your DC/OS cluster.\n'
