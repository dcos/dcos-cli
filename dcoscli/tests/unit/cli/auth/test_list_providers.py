from click.testing import CliRunner

from dcos_cli.cli.dcos import dcos


def test_list_providers():
    runner = CliRunner()
    result = runner.invoke(dcos, ['auth', 'list-providers'])
    assert result.exit_code == 0
    assert result.output == 'List authentication providers.\n'
