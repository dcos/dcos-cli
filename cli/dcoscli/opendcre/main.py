import os
import subprocess
import requests

import dcoscli
import docopt
from dcos import cmds, emitting, errors, mesos, util
from dcos.errors import DCOSException, DefaultError
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


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("opendcre"),
        argv=argv,
        version="opendcre version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
        cmds.Command(
            hierarchy=['opendcre', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['opendcre', 'scan'],
            arg_keys=[],
            function=_scan),

        cmds.Command(
            hierarchy=['opendcre', 'read'],
            arg_keys=['<device-type>', '<board-id>', '<device-id>'],
            function=_read),

        cmds.Command(
            hierarchy=['opendcre', 'asset'],
            arg_keys=['<board-id>', '<device-id>'],
            function=_asset),

    ]


def _info():
    """Print node cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("opendcre"))
    return 0


def _scan():
    """

    :return:
    """
    # FIXME - for the purposes of proof-of-concept, the url is just hardcoded here, should be changed!
    url = 'http://192.168.99.100:5000/vaporcore/1.0/scan'
    r = requests.get(url)

    if r.status_code == 200:
        emitter.publish(r.text)
    else:
        raise DCOSException("Failed to perform scan\n: {}".format(r.text))
    return 0


def _read(device_type, board_id, device_id):
    """

    :param device_type:
    :param board_id:
    :param device_id:
    :return:
    """
    # FIXME - for the purposes of proof-of-concept, the url is just hardcoded here, should be changed!
    url = 'http://192.168.99.100:5000/vaporcore/1.0/read/{}/{}/{}'.format(device_type, board_id, device_id)
    r = requests.get(url)

    if r.status_code == 200:
        emitter.publish(r.text)
    else:
        raise DCOSException("Failed to perform scan\n: {}".format(r.text))
    return 0


def _asset(board_id, device_id):
    """

    :param board_id:
    :param device_id:
    :return:
    """
    # FIXME - for the purposes of proof-of-concept, the url is just hardcoded here, should be changed!
    url = 'http://192.168.99.100:5000/vaporcore/1.0/asset/{}/{}'.format(board_id, device_id)
    r = requests.get(url)

    if r.status_code == 200:
        emitter.publish(r.text)
    else:
        raise DCOSException("Failed to retrieve asset information\n: {}".format(r.text))
    return 0
