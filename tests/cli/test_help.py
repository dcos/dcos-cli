from dcos.cli.help import main


def test_binary_directory():
    assert main._binary_directory('some/folder') == 'some/folder/bin'


def test_extract_subcommands():
    assert (main._extract_subcommands(['dcos-command', 'dcos-help']) ==
            ['command', 'help'])
