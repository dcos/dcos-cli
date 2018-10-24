import os
import posixpath
import sys
from functools import partial

import docopt
import six

import dcoscli
from dcos import cmds, config, emitting, mesos, util
from dcos.errors import DCOSException, DCOSHTTPException, DefaultError
from dcoscli import log, tables
from dcoscli import metrics
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import cluster_version_check, decorate_docopt_usage

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
    Redirects a failed command to /dev/null and prints the proper
    real_usage message, instead of just the usage string from usage.

    :param usage: The simplified usage string to parse
    :type usage: str
    :param real_usage: The original usage string to parse
    :type real_usage: str
    :param keywords: The keyword arguments to pass to docopt
    :type keywords: dict
    :returns: The parsed arguments
    :rtype: dict
    """

    base_subcommand = keywords.pop('base_subcommand')
    subcommand = keywords.pop('subcommand')

    try:
        stdout = sys.stdout

        # We run docopt twice (once with the real usage string and
        # once with the modified usage string) in order to populate
        # the 'real' arguments properly.
        with open(os.devnull, 'w') as nullfile:
            sys.stdout = nullfile
            real_arguments = docopt.docopt(
                real_usage,
                argv=[base_subcommand])
            arguments = docopt.docopt(
                usage,
                **keywords)
            sys.stdout = stdout

        real_arguments.update(arguments)
        real_arguments[subcommand] = True
        return real_arguments

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
@cluster_version_check
def _main(argv):
    """The main function for the 'task' subcommand"""

    # We must special case the 'dcos task exec' subcommand in order to
    # allow us to pass arguments to docopt in a more user-friendly
    # manner. Specifically, we need to be able to pass arguments
    # beginning with "-" to the command we are trying to launch with
    # 'exec' without docopt trying to match them to a named parameter
    # for the 'dcos' command itself.
    if len(argv) > 1 and argv[1] == "exec":
        args = docopt_wrapper(
            default_doc("task_exec"),
            default_doc("task"),
            argv=argv[2:],
            version="dcos-task version {}".format(dcoscli.version),
            options_first=True,
            base_subcommand="task",
            subcommand="exec")
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
            arg_keys=['--all', '--follow', '--completed', '--lines', '<task>',
                      '<file>'],
            function=_log),

        cmds.Command(
            hierarchy=['task', 'ls'],
            arg_keys=['<task>', '<path>', '--all', '--long', '--completed'],
            function=_ls),

        cmds.Command(
            hierarchy=['task', 'exec'],
            arg_keys=['<task>', '<cmd>', '<args>', '--interactive', '--tty'],
            function=_exec),

        cmds.Command(
            hierarchy=['task', 'metrics', 'details'],
            arg_keys=['<task-id>', '--json'],
            function=partial(_metrics, False)),

        cmds.Command(
            hierarchy=['task', 'metrics', 'summary'],
            arg_keys=['<task-id>', '--json'],
            function=partial(_metrics, True)),

        cmds.Command(
            hierarchy=['task'],
            arg_keys=['<task>', '--all', '--completed', '--json'],
            function=_task),
    ]


def _info():
    """Print task cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("task"))
    return 0


def _task(task, all_, completed, json_):
    """List DCOS tasks

    :param task: task id filter
    :type task: str
    :param all_: If True, include all tasks
    :type all_: bool
    :param completed: If True, include only completed tasks
    :type completed: bool
    :param json_: If True, output json.  Otherwise, output a human
                  readable table.
    :type json_: bool
    :returns: process return code
    """

    tasks = sorted(mesos.get_master().tasks(
        fltr=task, completed=completed, all_=all_),
        key=lambda t: t['name'])

    if json_:
        emitter.publish([t.dict() for t in tasks])
    else:
        table = tables.task_table(tasks)
        output = six.text_type(table)
        if output:
            emitter.publish(output)

    return 0


def _log(all_, follow, completed, lines, task, file_):
    """ Tail a file in the task's sandbox.

    :param all_: If True, include all tasks
    :type all_: bool
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
    tasks = master.tasks(fltr=fltr, completed=completed, all_=all_)

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

    # if journald logging is disabled, read files API and exit.
    if not log.dcos_log_enabled():
        mesos_files = _mesos_files(tasks, file_, client)
        if not mesos_files:
            if fltr is None:
                msg = "No tasks found. Exiting."
            else:
                msg = "No matching tasks. Exiting."
            raise DCOSException(msg)

        log.log_files(mesos_files, follow, lines)
        return 0

    # otherwise
    if file_ in ('stdout', 'stderr'):
        _dcos_log(follow, tasks, lines, file_, completed)
        return 0

    raise DCOSException('Invalid file {}. dcos-log only '
                        'supports stdout/stderr'.format(file_))
    return 1


def get_nested_container_id(task):
    """ Get the nested container id from mesos state.

    :param task: task definition
    :type task: dict
    :return: comma separated string of nested containers
    :rtype: string
    """

    # get current task state
    task_state = task.get('state')
    if not task_state:
        logger.debug('Full task state: {}'.format(task))
        raise DCOSException('Invalid executor info. '
                            'Missing field `state`')

    container_ids = []
    statuses = task.get('statuses')
    if not statuses:
        logger.debug('Full task state: {}'.format(task))
        raise DCOSException('Invalid executor info. Missing field `statuses`')

    for status in statuses:
        if 'state' not in status:
            logger.debug('Full task state: {}'.format(task))
            raise DCOSException('Invalid executor info. Missing field `state`')

        if status['state'] != task_state:
            continue

        container_status = status.get('container_status')
        if not container_status:
            logger.debug('Full task state: {}'.format(task))

            # if task status is TASK_FAILED and no container_id
            # available then the executor has never started and no
            # logs available for this task.
            if status.get('state') == 'TASK_FAILED':
                raise DCOSException('No available logs found. '
                                    'Please check your executor status')
            raise DCOSException('Invalid executor info. '
                                'Missing field `container_status`')

        container_id = container_status.get('container_id')
        if not container_id:
            logger.debug('Full task state: {}'.format(task))
            raise DCOSException('Invalid executor info. '
                                'Missing field `container_id`')

        # traverse nested container_id field
        while True:
            value = container_id.get('value')
            if not value:
                logger.debug('Full task state: {}'.format(task))
                raise DCOSException('Invalid executor info. Missing field'
                                    '`value` for nested container ids')

            container_ids.append(value)

            if 'parent' not in container_id:
                break

            container_id = container_id['parent']

    return '.'.join(reversed(container_ids))


def _dcos_log(follow, tasks, lines, file_, completed):
    """ a client to dcos-log

    :param follow: same as unix tail's -f
    :type follow: bool
    :param task: task pattern to match
    :type task: str
    :param lines: number of lines to print
    :type lines: int
    :param file_: file path to read
    :type file_: str
    :param completed: whether to include completed tasks
    :type completed: bool
    """

    # only stdout and stderr is supported
    if file_ not in ('stdout', 'stderr'):
        raise DCOSException('Expect file stdout or stderr. '
                            'Got {}'.format(file_))
    # state json may container tasks and completed_tasks fields. Based on
    # user request we should traverse the appropriate field.
    tasks_field = 'tasks'
    if completed:
        tasks_field = 'completed_tasks'

    for task in tasks:
        executor_info = task.executor()
        if not executor_info:
            continue
        if (tasks_field not in executor_info and
                not isinstance(executor_info[tasks_field], list)):
            logger.debug('Executor info: {}'.format(executor_info))
            raise DCOSException('Invalid executor info. '
                                'Missing field {}'.format(tasks_field))

        for t in executor_info[tasks_field]:
            container_id = get_nested_container_id(t)
            if not container_id:
                logger.debug('Executor info: {}'.format(executor_info))
                raise DCOSException(
                    'Invalid executor info. Missing container id')

            # get slave_id field
            slave_id = t.get('slave_id')
            if not slave_id:
                logger.debug('Executor info: {}'.format(executor_info))
                raise DCOSException(
                    'Invalid executor info. Missing field `slave_id`')

            framework_id = t.get('framework_id')
            if not framework_id:
                logger.debug('Executor info: {}'.format(executor_info))
                raise DCOSException(
                    'Invalid executor info. Missing field `framework_id`')

            # try `executor_id` first.
            executor_id = t.get('executor_id')
            if not executor_id:
                # if `executor_id` is an empty string, default to `id`.
                executor_id = t.get('id')
            if not executor_id:
                logger.debug('Executor info: {}'.format(executor_info))
                raise DCOSException(
                    'Invalid executor info. Missing executor id')

            dcos_url = config.get_config_val('core.dcos_url').rstrip('/')
            if not dcos_url:
                raise config.missing_config_exception(['core.dcos_url'])

            # dcos-log provides 2 base endpoints /range/ and /stream/
            # for range and streaming requests.
            endpoint_type = 'range'
            if follow:
                endpoint_type = 'stream'

            endpoint = ('/system/v1/agent/{}/logs/v1/{}/framework/{}'
                        '/executor/{}/container/{}'.format(slave_id,
                                                           endpoint_type,
                                                           framework_id,
                                                           executor_id,
                                                           container_id))
            # append request parameters.
            # `skip_prev` will move the cursor to -n lines.
            # `filter=STREAM:{STDOUT,STDERR}` will filter logs by label.
            url = (dcos_url + endpoint +
                   '?skip_prev={}&filter=STREAM:{}'.format(lines,
                                                           file_.upper()))

            if follow:
                return log.follow_logs(url)
            return log.print_logs_range(url)


def _ls(task, path, all_, long_, completed):
    """ List files in a task's sandbox.

    :param task: task pattern to match
    :type task: str
    :param path: file path to read
    :type path: str
    :param long_: whether to use a long listing format
    :type long_: bool
    :param all_: If True, include all tasks
    :type all_: bool
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
        fltr=task, completed=completed, all_=all_)

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


def _exec(task, cmd, args=None, interactive=False, tty=False):
    """ Launch a process inside a container with the given <task_id>

    :param task: task ID pattern to match
    :type task: str
    :param cmd: The command to launch inside the task's container
    :type args: cmd
    :param args: Additional arguments for the command
    :type args: list
    :param interactive: attach stdin
    :type interactive: bool
    :param tty: attach a tty
    :type tty: bool
    :returns: process return code
    :rtype int
    """

    task_io = mesos.TaskIO(task, cmd, args, interactive, tty)
    task_io.run()
    return 0


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


def _metrics(summary, task_id, json_):
    """
    Get metrics from the specified task.

    :param summary: summarise output if true, output all if false
    :type summary: bool
    :param task_id: mesos task id
    :type task_id: str
    :param json: print raw JSON
    :type json: bool
    :return: Process status
    :rtype: int
    """

    master = mesos.get_master()
    task = master.task(task_id)
    if 'slave_id' not in task:
        raise DCOSException(
            'Error finding agent associated with task: {}'.format(task_id))

    slave_id = task['slave_id']
    container_id = master.get_container_id(task)["value"]

    endpoint = '/system/v1/agent/{}/metrics/v0/containers/{}'.format(
        slave_id, container_id
    )
    dcos_url = config.get_config_val('core.dcos_url').rstrip('/')
    if not dcos_url:
        raise config.missing_config_exception(['core.dcos_url'])

    url = dcos_url + endpoint
    app_url = url + '/app'
    return metrics.print_task_metrics(url, app_url, summary, json_)
