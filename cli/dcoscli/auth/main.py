"""Store user authentication information

Usage:
    dcos auth --info
    dcos auth --config-schema

Options:
    -h, --help                   Show this screen
    --info                       Show a short description of this subcommand
    --config-schema              Show the configuration schema for the Marathon
                                 subcommand
"""

import json

import docopt
import pkg_resources
from dcos.api import cmds, emitting, options, util

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__)

    returncode, err = cmds.execute(_cmds(), args)
    if err is not None:
        emitter.publish(err)
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return returncode


def _cmds():

    return [cmds.Command(
        hierarchy=['auth'],
        arg_keys=['--config-schema', '--info'],
        function=_auth)]


def _auth(config_schema, info):
    if config_schema:
        schema = json.loads(
            pkg_resources.resource_string(
                'dcoscli',
                'data/config-schema/auth.json').decode('utf-8'))
        emitter.publish(schema)
        return 0
    elif info:
        emitter.publish(__doc__.split('\n')[0])
        return 0
    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1
