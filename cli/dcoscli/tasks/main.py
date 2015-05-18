"""Get the status of mesos tasks

Usage:
    dcos tasks --info
    dcos tasks [--completed --json <task>]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --json        Print json-formatted task data
    --completed   Show completed tasks as well
    --version     Show version

Positional Arguments:

    <task>        Only match tasks whose ID matches <task>.  <task> may be
                  a substring of the ID, or a unix glob pattern.
"""


from collections import OrderedDict

import blessings
import dcoscli
import docopt
import prettytable
from dcos import cmds, emitting, mesos, util
from dcos.errors import DCOSException

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _main():
    util.configure_logger_from_environ()

    args = docopt.docopt(
        __doc__,
        version="dcos-tasks version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
        cmds.Command(
            hierarchy=['tasks', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['tasks'],
            arg_keys=['<task>', '--completed', '--json'],
            function=_tasks),
    ]


def _info():
    """Print tasks cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _task_table(tasks):
    """Returns a PrettyTable representation of the provided tasks.

    :param tasks: tasks to render
    :type tasks: [Task]
    :rtype: TaskTable
    """

    term = blessings.Terminal()

    table_generator = OrderedDict([
        ("name", lambda t: t["name"]),
        ("user", lambda t: t.user()),
        ("state", lambda t: t["state"].split("_")[-1][0]),
        ("id", lambda t: t["id"]),
    ])

    tb = prettytable.PrettyTable(
        [k.upper() for k in table_generator.keys()],
        border=False,
        max_table_width=term.width,
        hrules=prettytable.NONE,
        vrules=prettytable.NONE,
        left_padding_width=0,
        right_padding_width=1
    )

    for task in tasks:
        row = [fn(task) for fn in table_generator.values()]
        tb.add_row(row)

    return tb


def _tasks(fltr, completed, is_json):
    """ List mesos tasks

    :param fltr: task id filter
    :type fltr: str
    :param completed: If True, include compelted tasks
    :type completed: bool
    :param is_json: If true, output json.
        Otherwise, output a human readable table.
    :type is_json: bool
    :returns: process return code
    """

    if fltr is None:
        fltr = ""

    master = mesos.get_master()
    tasks = sorted(master.tasks(active_only=(not completed), fltr=fltr),
                   key=lambda task: task['name'])

    if is_json:
        emitter.publish([task.dict() for task in tasks])
    else:
        table = _task_table(tasks)
        output = str(table)
        if output:
            emitter.publish(output)
