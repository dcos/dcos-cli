"""Manage DCOS tasks

Usage:
    dcos task --info
    dcos task [--completed --json <task>]
    dcos task log [--completed --follow --lines=N] <task> [<file>]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --completed   Include completed tasks as well
    --follow      Output data as the file grows
    --json        Print json-formatted tasks
    --lines=N     Output the last N lines [default: 10]
    --version     Show version

Positional Arguments:

    <task>        Only match tasks whose ID matches <task>.  <task> may be
                  a substring of the ID, or a unix glob pattern.

    <file>        Output this file. [default: stdout]
"""

import dcoscli
import docopt
from dcos import cmds, emitting, mesos, util
from dcos.errors import DCOSException, DefaultError
from dcoscli import log, tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _main():
    util.configure_process_from_environ()

    args = docopt.docopt(
        __doc__,
        version="dcos-task version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
        cmds.Command(
            hierarchy=['task', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['task', 'log'],
            arg_keys=['--follow', '--completed', '--lines', '<task>',
                      '<file>'],
            function=_log),

        cmds.Command(
            hierarchy=['task'],
            arg_keys=['<task>', '--completed', '--json'],
            function=_task),
    ]


def _info():
    """Print task cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _task(fltr, completed, json_):
    """List DCOS tasks

    :param fltr: task id filter
    :type fltr: str
    :param completed: If True, include completed tasks
    :type completed: bool
    :param json_: If True, output json.  Otherwise, output a human
                  readable table.
    :type json_: bool
    :returns: process return code
    """

    if fltr is None:
        fltr = ""

    tasks = sorted(mesos.get_master().tasks(completed=completed, fltr=fltr),
                   key=lambda task: task['name'])

    if json_:
        emitter.publish([task.dict() for task in tasks])
    else:
        table = tables.task_table(tasks)
        output = str(table)
        if output:
            emitter.publish(output)

    return 0


def _log(follow, completed, lines, task, file_):
    """ Tail a file in the task's sandbox.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param completed: whether to include completed tasks
    :type completed: bool
    :param lines: number of lines to print
    :type lines: int
    :param task: task pattern to match
    :type task: str
    :param file_: file path to read
    :type file_: str
    :returns: process return code
    :rtype: int
    """

    if task is None:
        fltr = ""
    else:
        fltr = task

    if file_ is None:
        file_ = 'stdout'

    lines = util.parse_int(lines)

    mesos_files = _mesos_files(completed, fltr, file_)
    if not mesos_files:
        raise DCOSException('No matching tasks. Exiting.')
    log.log_files(mesos_files, follow, lines)

    return 0


def _mesos_files(completed, fltr, file_):
    """Return MesosFile objects for the specified files.  Only include
    files that satisfy all of the following:

    a) belong to an available slave
    b) have an executor entry on the slave

    :param completed: whether to include completed tasks
    :type completed: bool
    :param fltr: task pattern to match
    :type fltr: str
    :param file_: file path to read
    :type file_: str
    :returns: MesosFile objects
    :rtype: [MesosFile]

    """

    # get tasks
    client = mesos.DCOSClient()
    master = mesos.Master(client.get_master_state())
    tasks = master.tasks(completed=completed, fltr=fltr)

    # load slave state in parallel
    slaves = _load_slaves_state([task.slave() for task in tasks])

    # some completed tasks may have entries on the master, but none on
    # the slave.  since we need the slave entry to get the executor
    # sandbox, we only include files with an executor entry.
    available_tasks = [task for task in tasks
                       if task.slave() in slaves and task.executor()]

    # create files.
    return [mesos.MesosFile(file_, task=task, dcos_client=client)
            for task in available_tasks]


def _load_slaves_state(slaves):
    """Fetch each slave's state.json in parallel, and return the reachable
    slaves.

    :param slaves: slaves to fetch
    :type slaves: [MesosSlave]
    :returns: MesosSlave objects that were successfully reached
    :rtype: [MesosSlave]
    """

    reachable_slaves = []

    for job, slave in util.stream(lambda slave: slave.state(), slaves):
        try:
            job.result()
            reachable_slaves.append(slave)
        except DCOSException as e:
            emitter.publish(
                DefaultError('Error accessing slave: {0}'.format(e)))

    return reachable_slaves
