import docopt
import os
import posixpath

import docopt
import six
import sys
import termios

import dcoscli
from dcos import cmds, emitting, mesos, util
from dcos.errors import DCOSException, DCOSHTTPException, DefaultError
from dcoscli import log, tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


def docopt_wrapper(usage, real_usage, **keywords):
    """ A wrapper around the real docopt parser.
    Redirects a failed exec command to /dev/null and prints the proper
    real_usage message, instead of just the usage string from dcos-task-exec

    :param usage: task id filter
    :type usage: str
    :param real_usage: If True, include completed tasks
    :type real_usage: bool
    :param keywords: If True, output json.  Otherwise, output a human
                  readable table.
    :type keywords: bool
    :returns: process return code
    """

    try:
        stdout = sys.stdout

        with open(os.devnull, 'w') as nullfile:
            sys.stdout = nullfile
            arguments = docopt.docopt(usage, **keywords)
            sys.stdout = stdout

        return arguments

    except docopt.DocoptExit:
        sys.stdout = stdout
        print(real_usage.strip(), file=sys.stderr)
        sys.exit(1)

    except SystemExit:
        sys.stdout = stdout

        if "argv" in keywords and any(h in ("-h", "--help")
                                      for h in keywords["argv"]):
            print(real_usage.strip())
        elif "version" in keywords and any(v in ("--version")
                                           for v in keywords["argv"]):
            print(keywords["version"].strip())

        sys.exit()


@decorate_docopt_usage
def _main(argv):
    """This usage string rewriting is necessary in order to allow 
    passing arguments beginning with "-" to _exec without
    docopt trying to match them to a named parameter.

    Setting args['xyz'] to True/False is done because docopt does
    the same internally, and expects to be able to test each of them
    to determine which parameters should match. If more commands are added
    to /dcos-cli/cli/dcoscli/data/help/task.txt they will need to be set to False
    in this function.
    """

    if len(argv) > 1 and argv[1] == "exec":
        usage = \
        '''
        Usage:
            dcos-task-exec [--interactive --tty] <task> <cmd> [<args>...]
        '''
        args = docopt_wrapper(
            usage,
            default_doc("task"),
            argv=argv[2:],
            version="dcos-task version {}".format(dcoscli.version),
            options_first=True)

        args['task'] = True
        args['exec'] = True
        args['log'] = False
        args['ls'] = False
        args['--info'] = False
    else:
         args = docopt.docopt(
            default_doc("task"),
            argv=argv,
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
            arg_keys=['<task>', '<path>', '--long', '--completed'],
            function=_ls),

        cmds.Command(
            hierarchy=['task', 'exec'],
            arg_keys=['<task>', '<cmd>', '--interactive', '--tty', '<args>'],
            function=_exec),

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

    emitter.publish(default_command_info("task"))
    return 0


def _task(task, completed, json_):
    """List DCOS tasks

    :param task: task id filter
    :type task: str
    :param completed: If True, include completed tasks
    :type completed: bool
    :param json_: If True, output json.  Otherwise, output a human
                  readable table.
    :type json_: bool
    :returns: process return code
    """

    tasks = sorted(mesos.get_master().tasks(completed=completed, fltr=task),
                   key=lambda t: t['name'])

    if json_:
        emitter.publish([t.dict() for t in tasks])
    else:
        table = tables.task_table(tasks)
        output = six.text_type(table)
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

    fltr = task

    if file_ is None:
        file_ = 'stdout'

    if lines is None:
        lines = 10
    lines = util.parse_int(lines)

    # get tasks
    client = mesos.DCOSClient()
    master = mesos.Master(client.get_master_state())
    tasks = master.tasks(completed=completed, fltr=fltr)

    if not tasks:
        if not fltr:
            raise DCOSException("No tasks found. Exiting.")
        elif not completed:
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
        if fltr is None:
            msg = "No tasks found. Exiting."
        else:
            msg = "No matching tasks. Exiting."
        raise DCOSException(msg)

    log.log_files(mesos_files, follow, lines)

    return 0


def _ls(task, path, long_, completed):
    """ List files in a task's sandbox.

    :param task: task pattern to match
    :type task: str
    :param path: file path to read
    :type path: str
    :param long_: whether to use a long listing format
    :type long_: bool
    :param completed: If True, include completed tasks
    :type completed: bool
    :returns: process return code
    :rtype: int
    """

    if path is None:
        path = '.'
    if path.startswith('/'):
        path = path[1:]

    dcos_client = mesos.DCOSClient()
    task_objects = mesos.get_master(dcos_client).tasks(
        fltr=task,
        completed=completed)

    if len(task_objects) == 0:
        if task is None:
            raise DCOSException("No tasks found")
        else:
            raise DCOSException(
                'Cannot find a task with ID containing "{}"'.format(task))

    try:
        all_files = []
        for task_obj in task_objects:
            dir_ = posixpath.join(task_obj.directory(), path)
            all_files += [
                (task_obj['id'], dcos_client.browse(task_obj.slave(), dir_))]
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
            raise DCOSException(
                'Cannot access [{}]: No such file or directory'.format(path))
        else:
            raise

    add_header = len(all_files) > 1
    for (task_id, files) in all_files:
        if add_header:
            emitter.publish('===> {} <==='.format(task_id))
        if long_:
            emitter.publish(tables.ls_long_table(files))
        else:
            emitter.publish(
                '  '.join(posixpath.basename(file_['path'])
                          for file_ in files))


def _exec(task, cmd, interactive=False, tty=False, args=None):
    """ Launch a process inside a container with the given <task_id>

    :param task: task ID pattern to match
    :type task: str
    :param interactive: attach stdin
    :type interactive: bool
    :param tty: attach a tty
    :type tty: bool
    :param args: Additional arguments for the command
    :type args: str
    """

    taskIO = mesos.TaskIO(task, cmd, interactive, tty, args)
    taskIO.run()


def _mesos_files(tasks, file_, client):
    """Return MesosFile objects for the specified tasks and file name.
    Only include files that satisfy all of the following:

    a) belong to an available slave
    b) have an executor entry on the slave

    :param tasks: tasks on which files reside
    :type tasks: [mesos.Task]
    :param file_: file path to read
    :type file_: str
    :param client: DC/OS client
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
