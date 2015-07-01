"""Manage DCOS services

Usage:
    dcos service --info
    dcos service [--inactive --json]
    dcos service shutdown <service-id>

Options:
    -h, --help    Show this screen

    --info        Show a short description of this subcommand

    --json        Print json-formatted services

    --inactive    Show inactive services in addition to active ones.
                  Inactive services are those that have been disconnected from
                  master, but haven't yet reached their failover timeout.

    --version     Show version

Positional Arguments:
    <service-id>  The ID for the DCOS Service
"""

import dcoscli
import docopt
from dcos import cmds, emitting, mesos, util
from dcos.errors import DCOSException
from dcoscli import tables

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
        version="dcos-service version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
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
            arg_keys=['--inactive', '--json'],
            function=_service),
    ]


def _info():
    """Print services cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


# TODO (mgummelt): support listing completed services as well.
# blocked on framework shutdown.
def _service(inactive, is_json):
    """List dcos services

    :param inactive: If True, include completed tasks
    :type inactive: bool
    :param is_json: If true, output json.
        Otherwise, output a human readable table.
    :type is_json: bool
    :returns: process return code
    :rtype: int
    """

    services = mesos.get_master().frameworks(inactive=inactive)

    if is_json:
        emitter.publish([service.dict() for service in services])
    else:
        table = tables.service_table(services)
        output = str(table)
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
