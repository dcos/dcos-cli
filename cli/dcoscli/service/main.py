"""Get the status of DCOS services

Usage:
    dcos service --info
    dcos service [--inactive --json]

Options:
    -h, --help    Show this screen

    --info        Show a short description of this subcommand

    --json        Print json-formatted services

    --inactive    Show inactive services in addition to active ones.
                  Inactive services are those that have been disconnected from
                  master, but haven't yet reached their failover timeout.

    --version     Show version
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
        version="dcos-service version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
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


def _service_table(services):
    """Returns a PrettyTable representation of the provided services.

    :param services: services to render
    :type services: [Framework]
    :rtype: TaskTable
    """

    term = blessings.Terminal()

    table_generator = OrderedDict([
        ("name", lambda s: s['name']),
        ("host", lambda s: s['hostname']),
        ("active", lambda s: s['active']),
        ("tasks", lambda s: len(s['tasks'])),
        ("cpu", lambda s: s['resources']['cpus']),
        ("mem", lambda s: s['resources']['mem']),
        ("disk", lambda s: s['resources']['disk']),
        ("ID", lambda s: s['id']),
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

    for service in services:
        row = [fn(service) for fn in table_generator.values()]
        tb.add_row(row)

    return tb


# TODO (mgummelt): support listing completed services as well.
# blocked on framework shutdown.
def _service(inactive, is_json):
    """List dcos services

    :param inactive: If True, include completed tasks
    :type completed: bool
    :param is_json: If true, output json.
        Otherwise, output a human readable table.
    :type is_json: bool
    :returns: process return code
    :rtype: int
    """

    master = mesos.get_master()
    services = master.frameworks(inactive=inactive)

    if is_json:
        emitter.publish([service.dict() for service in services])
    else:
        table = _service_table(services)
        output = str(table)
        if output:
            emitter.publish(output)

    return 0
