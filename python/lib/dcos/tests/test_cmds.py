import pytest

from dcos import cmds


@pytest.fixture
def args():
    return {
        'cmd-a': True,
        'cmd-b': True,
        'cmd-c': False,
        'arg-1': 'arg-1',
        'arg-2': 'arg-2',
        'arg-0': 'arg-0',
    }


def test_single_cmd(args):
    commands = [
        cmds.Command(
            hierarchy=['cmd-a', 'cmd-b'],
            arg_keys=['arg-0', 'arg-1', 'arg-2'],
            function=function),
    ]

    assert cmds.execute(commands, args) == 1


def test_multiple_cmd(args):
    commands = [
        cmds.Command(
            hierarchy=['cmd-c'],
            arg_keys=['arg-0', 'arg-1', 'arg-2'],
            function=pytest.fail),
        cmds.Command(
            hierarchy=['cmd-a', 'cmd-b'],
            arg_keys=['arg-0', 'arg-1', 'arg-2'],
            function=function),
    ]

    assert cmds.execute(commands, args) == 1


def test_no_matching_cmd(args):
    commands = [
        cmds.Command(
            hierarchy=['cmd-c'],
            arg_keys=['arg-0', 'arg-1', 'arg-2'],
            function=pytest.fail),
    ]

    with pytest.raises(Exception):
        cmds.execute(commands, args)


def test_similar_cmds(args):
    commands = [
        cmds.Command(
            hierarchy=['cmd-a', 'cmd-b'],
            arg_keys=['arg-0', 'arg-1', 'arg-2'],
            function=function),
        cmds.Command(
            hierarchy=['cmd-a'],
            arg_keys=['arg-0', 'arg-1', 'arg-2'],
            function=pytest.fail),
    ]

    assert cmds.execute(commands, args) == 1


def test_missing_cmd(args):
    commands = [
        cmds.Command(
            hierarchy=['cmd-d'],
            arg_keys=['arg-0', 'arg-1', 'arg-2'],
            function=pytest.fail),
    ]

    with pytest.raises(KeyError):
        returncode, err = cmds.execute(commands, args)


def test_missing_arg(args):
    commands = [
        cmds.Command(
            hierarchy=['cmd-a'],
            arg_keys=['arg-3'],
            function=pytest.fail),
    ]

    with pytest.raises(KeyError):
        returncode, err = cmds.execute(commands, args)


def function(*args):
    for i in range(len(args)):
        assert args[i] == 'arg-{}'.format(i)

    return 1
