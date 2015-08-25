"""Manage DCOS tasks

Usage:
    dcos task --info
    dcos task [--completed --json <task>]
    dcos task log [--completed --follow --lines=N] <task> [<file>]
    dcos task ls [--long] <task> [<path>]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --completed   Include completed tasks as well
    --follow      Print data as the file grows
    --json        Print json-formatted tasks
    --lines=N     Print the last N lines [default: 10]
    --long        Use a long listing format
    --version     Show version

Positional Arguments:
    <file>        Print this file. [default: stdout]
    <path>        List this directory. [default: '.']
    <task>        Only match tasks whose ID matches <task>.  <task> may be
                  a substring of the ID, or a unix glob pattern.
"""

import posixpath

import dcoscli
import docopt
from dcos import cmds, emitting, mesos, util
from dcos.errors import DCOSException, DCOSHTTPException, DefaultError
from dcoscli import log, tables
from dcoscli.main import decorate_docopt_usage

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
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
            hierarchy=['task', 'ls'],
            arg_keys=['<task>', '<path>', '--long'],
            function=_ls),

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

    # get tasks
    client = mesos.DCOSClient()
    master = mesos.Master(client.get_master_state())
    tasks = master.tasks(completed=completed, fltr=fltr)

    if not tasks:
        if not completed:
            completed_tasks = master.tasks(completed=True, fltr=fltr)
            if completed_tasks:
                msg = 'No running tasks match ID [{}]; however, there '.format(
                    fltr)
                if len(completed_tasks) > 1:
                    msg += 'are {} matching completed tasks. '.format(
                        len(completed_tasks))
                else:
                    msg += 'is 1 matching completed task. '
                msg += 'Run with --completed to see these logs.'
                raise DCOSException(msg)
        raise DCOSException('No matching tasks. Exiting.')

    mesos_files = _mesos_files(tasks, file_, client)
    if not mesos_files:
        raise DCOSException('No matching tasks. Exiting.')

    log.log_files(mesos_files, follow, lines)

    return 0


def _ls(task, path, long_):
    """ List files in a task's sandbox.

    :param task: task pattern to match
    :type task: str
    :param path: file path to read
    :type path: str
    :param long_: whether to use a long listing format
    :type long_: bool
    :returns: process return code
    :rtype: int
    """

    if path is None:
        path = '.'
    if path.startswith('/'):
        path = path[1:]

    dcos_client = mesos.DCOSClient()
    task_obj = mesos.get_master(dcos_client).task(task)
    dir_ = posixpath.join(task_obj.directory(), path)

    try:
        files = dcos_client.browse(task_obj.slave(), dir_)
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
            raise DCOSException(
                'Cannot access [{}]: No such file or directory'.format(path))
        else:
            raise

    if files:
        if long_:
            emitter.publish(tables.ls_long_table(files))
        else:
            emitter.publish(
                '  '.join(posixpath.basename(file_['path'])
                          for file_ in files))


def _mesos_files(tasks, file_, client):
    """Return MesosFile objects for the specified tasks and file name.
    Only include files that satisfy all of the following:

    a) belong to an available slave
    b) have an executor entry on the slave

    :param tasks: tasks on which files reside
    :type tasks: [mesos.Task]
    :param file_: file path to read
    :type file_: str
    :param client: DCOS client
    :type client: mesos.DCOSClient
    :returns: MesosFile objects
    :rtype: [mesos.MesosFile]
    """

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
