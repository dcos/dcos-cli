"""Get the status of the DCOS cluster

Usage:
   dcos status --info
   dcos status --version
   dcos status [--json]

Options:
    --help                  Show this screen
    --info                  Show info
    --json                  Print json-formatted cluster status
    --version               Show version
"""
import dcoscli
import docopt
from dcos import cmds, emitting, marathon, mesos, util
from dcos.errors import DCOSException
from dcos.http import request
from dcoscli import tables

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()

OK_STATUS = 200


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
        version='dcos-status version {}'.format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
        cmds.Command(
            hierarchy=['status', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['status'],
            arg_keys=['--json'],
            function=_status),
        ]


def _status(is_json):
    """ Print to cli cluster status

    :param: is_json: dcos cluster input arguments
    :type: is_json: boolean
    """
    cluster_data, exit_code = _get_cluster_data()
    emitting.publish_table(emitter, cluster_data,
                           tables.cluster_table, is_json)
    if exit_code != 0:
        raise DCOSException()


def _info():
    """Print Dcos cluster status cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _get_cluster_data():
    """ Get information about current cli cluster

    :returns: Cluster status data
    :rtype: dict
    """
    exit_code_list = list()

    def sum_codes(f):
        status, exit_code = f()
        exit_code_list.append(exit_code)
        return status

    return [{'Name': 'Mesos Master',
             'Status': sum_codes(_check_master_status)},
            {'Name': 'Mesos Marathon framework',
             'Status': sum_codes(_check_marathon_task_status)},
            {'Name': 'Mesos active Slaves count',
             'Status': sum_codes(_get_active_slaves_number)},
            {'Name': 'Marathon', 'Status': sum_codes(_check_marathon_status)},
            {'Name': 'DCOS UI', 'Status': sum_codes(_check_ui_status)},
            {'Name': 'Exhibitor',  'Status':
                sum_codes(_check_exhibitor_status)}], sum(exit_code_list)


def _get_dcos_url():
    """Return a Mesos master client URL, using the URLs stored in the user's
    configuration.

    :returns: mesos master url
    :rtype: str
    """
    config = util.get_config()
    dcos_url = util.get_config_vals(config, ['core.dcos_url'])[0]
    return dcos_url


def _check_master_status():
    """Check Mesos Master status on current cluster

    :returns: tuple, which contain status and exit code
    :rtype (str, int)
    """
    return _make_request(mesos.get_master_client().get_state)


def _check_marathon_task_status():
    """Check task with name "marathon" exist on current cluster

    :returns: tuple, which contain status and exit code
    :rtype (str, int)
    """
    try:
        state = mesos.get_master_client().get_state()
        frameworks = state['frameworks']
        if any(f['name'] == 'marathon' for f in frameworks):
            return 'OK', 0
        else:
            return 'Marathon framework is not registered.', 1
    except DCOSException:
        return 'Error. Unable to get Marathon framework status.', 1


def _get_active_slaves_number():
    """Get all active Mesos slaves number on current cluster

    :returns: tuple, which contain status and exit code
    :rtype (str, int)
    """

    try:
        state = mesos.get_master_client().get_state()
        return state['activated_slaves'], 0
    except DCOSException:
        return 'Error. Unable to get Mesos slaves count.', 1


def _check_marathon_status():
    """Check Marathon status on current cluster

    :returns: tuple, which contain status and exit code
    :rtype (str, int)
    """

    return _make_request(marathon.create_client().get_about)


def _check_ui_status():
    """Check DCOS UI status on current cluster

    :returns: tuple, which contain status and exit code
    :rtype (str, int)
    """

    return _make_request(request, "GET", '{}:80'.format(_get_dcos_url()))


def _check_exhibitor_status():
    """Check Exhibitor status on current cluster

    :returns: tuple, which contain status and exit code
    :rtype (str, int)
    """

    return _make_request(request, "GET", '{}:8181/exhibitor/v1/cluster/'
                         'status'.format(_get_dcos_url()))


def _make_request(check_function, *args):
    """Execute request to DCOS components
    :param: check_function: function used to make component check call
    :type: check_function: args -> None
    :returns: tuple, which contain status and exit code
    :rtype (str, int)
    """
    try:
        if len(args) > 0:
            check_function(*args)
        else:
            check_function()
        return "OK", 0
    except DCOSException:
        return "Error", 1
