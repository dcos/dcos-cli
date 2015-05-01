from dcos import subcommand


def test_noun():
    assert subcommand.noun("some/path/to/dcos-command") == "command"


def test_hyphen_noun():
    assert subcommand.noun("some/path/to/dcos-sub-command") == "sub-command"
