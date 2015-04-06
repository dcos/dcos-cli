"""Install and manage DCOS CLI subcommands

Usage:
    dcos subcommand --config-schema
    dcos subcommand --info
    dcos subcommand info
    dcos subcommand install <package>
    dcos subcommand list
    dcos subcommand uninstall <package_name>

Options:
    --help     Show this screen
    --info     Show a short description of this subcommand
    --version  Show version

Positional arguments:
    <package>          The subcommand package wheel
    <package_name>     The name of the subcommand package
"""
import json
import os

import dcoscli
import docopt
import pkg_resources
import pkginfo
from dcos.api import (cmds, config, constants, emitting, errors, options,
                      subcommand, util)

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-subcommand version {}'.format(dcoscli.version))

    returncode, err = cmds.execute(_cmds(), args)
    if err is not None:
        emitter.publish(err)
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return returncode


def _cmds():
    """
    :returns: all the supported commands
    :rtype: dcos.api.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['subcommand', 'install'],
            arg_keys=['<package>'],
            function=_install),

        cmds.Command(
            hierarchy=['subcommand', 'uninstall'],
            arg_keys=['<package_name>'],
            function=_uninstall),

        cmds.Command(
            hierarchy=['subcommand', 'list'],
            arg_keys=[],
            function=_list),

        cmds.Command(
            hierarchy=['subcommand'],
            arg_keys=['--config-schema', '--info'],
            function=_subcommand),
    ]


def _subcommand(config_schema, info):
    """
    :returns: Process status
    :rtype: int
    """

    if config_schema:
        schema = json.loads(
            pkg_resources.resource_string(
                'dcoscli',
                'data/config-schema/subcommand.json').decode('utf-8'))
        emitter.publish(schema)
    elif info:
        _info()
    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return 0


def _info():
    """
    :returns: the process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _list():
    """
    :returns: the process return code
    :rtype: int
    """

    emitter.publish(subcommand.distributions(util.dcos_path()))

    return 0


def _install(package):
    """
    :returns: the process return code
    :rtype: int
    """

    dcos_config = config.load_from_path(os.environ[constants.DCOS_CONFIG_ENV])

    install_operation = {
        'pip': [package]
    }
    if 'subcommand.pip_find_links' in dcos_config:
        install_operation['pip'].append(
            '--find-links {}'.format(dcos_config['subcommand.pip_find_links']))

    distribution_name, err = _distribution_name(package)
    if err is not None:
        emitter.publish(err)
        return 1

    err = subcommand.install(
        distribution_name,
        install_operation,
        util.dcos_path())
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _uninstall(package_name):
    """
    :returns: the process return code
    :rtype: int
    """

    subcommand.uninstall(package_name, util.dcos_path())

    return 0


def _distribution_name(package_path):
    """
    :returns: the distribution's name
    :rtype: (str, dcos.api.errors.Error)
    """

    try:
        return (pkginfo.Wheel(package_path).name, None)
    except ValueError as error:
        logger.error('Failed to read wheel (%s): %r', package_path, error)
        return (
            None,
            errors.DefaultError(
                'Failed to read file: {}'.format(error))
        )
