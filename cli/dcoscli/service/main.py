import email
import io
import json
import sys

import docopt
import six

import dcoscli
from dcos import cmds, emitting, http, marathon, mesos, subprocess, util
from dcos.errors import DCOSException, DefaultError
from dcoscli import log, tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

from ..task import main as task_main

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("service"),
        argv=argv,
        version="dcos-service version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
        cmds.Command(
            hierarchy=['service', 'http'],
            arg_keys=['--method', '--data', '--header', '--cookie', '--output', '<service>', '<request-path>'],
            function=_http),

        cmds.Command(
            hierarchy=['service', 'log'],
            arg_keys=['--follow', '--lines', '--ssh-config-file', '<service>',
                      '<file>'],
            function=_log),

        cmds.Command(
            hierarchy=['service', 'shutdown'],
            arg_keys=['<service-id>'],
            function=_shutdown),

        cmds.Command(
            hierarchy=['service', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['service'],
            arg_keys=['--inactive', '--completed', '--json'],
            function=_service),
    ]


def _info():
    """Print services cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("service"))
    return 0


def _service(inactive, completed, is_json):
    """List dcos services

    :param inactive: If True, include completed tasks
    :type inactive: bool
    :param is_json: If true, output json.
        Otherwise, output a human readable table.
    :type is_json: bool
    :returns: process return code
    :rtype: int
    """

    services = mesos.get_master().frameworks(
        inactive=inactive,
        completed=completed)

    if is_json:
        emitter.publish([service.dict() for service in services])
    else:
        table = tables.service_table(services)
        output = six.text_type(table)
        if output:
            emitter.publish(output)

    return 0


def _shutdown(service_id):
    """Shuts down a service

    :param service_id: the id for the service
    :type service_id: str
    :returns: process return code
    :rtype: int
    """

    mesos.DCOSClient().shutdown_framework(service_id)
    return 0


def _http(method, data, headers, cookie, output_file, service, path):
    """Do HTTP request to a service

    :param method: HTTP method (e.g.: "GET", "POST", "PUT", etc.)
    :type method: str
    :param data: Data for HTTP request body
    :type method: str
    :param cookie: Cookie data for HTTP request
    :type method: str
    :param service: the id for the service
    :type service: str
    :param path: path to include in request URL to service
    :type path: str
    :returns: process return code
    :rtype: int
    """

    if not path.startswith('/'):
        path = '/' + path
    url = mesos.DCOSClient().get_dcos_url('service/' + service + path)
    sys.stderr.write('>>> %s %s\n' % (method, url))
    http_func = getattr(http, method.lower())
    headers_dict = {}
    kwargs = {'headers': headers_dict}
    if data is not None:
        if data == '-':
            data = sys.stdin.read()
        if data.startswith('@'):
            with open(data[1:]) as f:
                data = f.read()
        kwargs['data'] = data
    for header in headers:
        message = email.message_from_file(io.StringIO(header))
        for key, val in message.items():
            headers_dict[key] = val
    if cookie:
        headers_dict['Cookie'] = cookie
    response = http_func(url, **kwargs)

    if output_file:
        f = open(output_file, 'w')
        sys.stdout = f

    try:
        emitter.publish(response.json())
    except json.JSONDecodeError:
        emitter.publish(response.text)
    finally:
        if output_file:
            sys.stdout = sys.__stdout__
            print('Output written to %s' % output_file)
            f.close()

    return 0


def _log(follow, lines, ssh_config_file, service, file_):
    """Prints the contents of the logs for a given service.  The service
    task is located by first identifying the marathon app running a
    framework named `service`.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param ssh_config_file: SSH config file.  Used for marathon.
    :type ssh_config_file: str | None
    :param service: service name
    :type service: str
    :param file_: file path to read
    :type file_: str
    :returns: process return code
    :rtype: int
    """

    if lines is None:
        lines = 10
    lines = util.parse_int(lines)

    if service == 'marathon':
        if file_:
            raise DCOSException('The <file> argument is invalid for marathon.'
                                ' The systemd journal is always used for the'
                                ' marathon log.')

        return _log_marathon(follow, lines, ssh_config_file)
    else:
        if ssh_config_file:
            raise DCOSException(
                'The `--ssh-config-file` argument is invalid for non-marathon '
                'services. SSH is not used.')
        return _log_service(follow, lines, service, file_)


def _log_service(follow, lines, service, file_):
    """Prints the contents of the logs for a given service.  Used for
    non-marathon services.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param service: service name
    :type service: str
    :param file_: file path to read
    :type file_: str
    :returns: process return code
    :rtype: int
    """

    if file_ is None:
        file_ = 'stdout'

    task = _get_service_task(service)

    # if journald logging is disabled, read from files API.
    if not log.dcos_log_enabled():
        return _log_task(task['id'], follow, lines, file_)

    if 'id' not in task:
        raise DCOSException('Missing `id` in task. {}'.format(task))

    task_id = task['id']
    task_main._log(follow, False, lines, task_id, file_)
    return 0


def _log_task(task_id, follow, lines, file_):
    """Prints the contents of the logs for a given task ID.

    :param task_id: task ID
    :type task_id: str
    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param file_: file path to read
    :type file_: str
    :returns: process return code
    :rtype: int
    """

    dcos_client = mesos.DCOSClient()
    task = mesos.get_master(dcos_client).task(task_id)
    mesos_file = mesos.MesosFile(file_, task=task, dcos_client=dcos_client)
    return log.log_files([mesos_file], follow, lines)


def _get_service_task(service_name):
    """Gets the task running the given service.  If there is more than one
    such task, throws an exception.

    :param service_name: service name
    :type service_name: str
    :returns: The marathon task dict
    :rtype: dict
    """

    marathon_client = marathon.create_client()
    app = _get_service_app(marathon_client, service_name)
    tasks = marathon_client.get_app(app['id'])['tasks']
    if len(tasks) != 1:
        raise DCOSException(
            ('We expected marathon app [{}] to be running 1 task, but we ' +
             'instead found {} tasks').format(app['id'], len(tasks)))
    return tasks[0]


def _get_service_app(marathon_client, service_name):
    """Gets the marathon app running the given service.  If there is not
    exactly one such app, throws an exception.

    :param marathon_client: marathon client
    :type marathon_client: marathon.Client
    :param service_name: service name
    :type service_name: str
    :returns: marathon app
    :rtype: dict
    """

    apps = marathon_client.get_apps_for_framework(service_name)

    if len(apps) > 1:
        raise DCOSException(
            'Multiple marathon apps found for service name [{}]: {}'.format(
                service_name,
                ', '.join('[{}]'.format(app['id']) for app in apps)))
    elif len(apps) == 0:
        raise DCOSException(
            'No marathon apps found for service [{}]'.format(service_name))
    else:
        return apps[0]


def _log_marathon(follow, lines, ssh_config_file):
    """Prints the contents of the marathon logs. Proxy through the master
    because marathon only runs on the master.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param ssh_config_file: SSH config file.
    :type ssh_config_file: str | None
    ;:returns: process return code
    :rtype: int
    """

    ssh_options = util.get_ssh_options(ssh_config_file, [])

    journalctl_args = ''
    if follow:
        journalctl_args += '-f '
    if lines:
        journalctl_args += '-n {} '.format(lines)

    leader_ip = marathon.create_client().get_leader().split(':')[0]
    user_string = 'core@'
    if ssh_config_file:
        user_string = ''

    dcos_client = mesos.DCOSClient()
    master_public_ip = dcos_client.metadata().get('PUBLIC_IPV4')
    service = 'dcos-marathon'

    cmd = "ssh -At {0}{1}{2} ssh -At {0}{1}{3} journalctl {4}-u {5}".format(
        ssh_options,
        user_string,
        master_public_ip,
        leader_ip,
        journalctl_args,
        service)

    emitter.publish(DefaultError("Running `{}`".format(cmd)))

    return subprocess.Subproc().call(cmd, shell=True)
