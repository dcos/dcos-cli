"""Get and set DCOS command line options

Usage:
    dcos config info
    dcos config set <name> <value>
    dcos config unset <name>
    dcos config show [<name>]

Options:
    -h, --help            Show this screen
    --version             Show version
"""

import collections
import os

import docopt
import toml
from dcos.api import cmds, config, constants, emitting, errors, options, util

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-config version {}'.format(constants.version))

    returncode, err = cmds.execute(_cmds(), args)
    if err is not None:
        emitter.publish(err)
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return returncode


def _cmds():
    """
    :returns: all the supported commands
    :rtype: list of dcos.api.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['config', 'info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['config', 'set'],
            arg_keys=['<name>', '<value>'],
            function=_set),

        cmds.Command(
            hierarchy=['config', 'unset'],
            arg_keys=['<name>'],
            function=_unset),

        cmds.Command(
            hierarchy=['config', 'show'],
            arg_keys=['<name>'],
            function=_show),
    ]


def _info():
    """
    :returns: process status
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _set(name, value):
    """
    :returns: process status
    :rtype: int
    """

    config_path, toml_config = _load_config()
    toml_config[name] = value
    _save_config_file(config_path, toml_config)

    return 0


def _unset(name):
    """
    :returns: process status
    :rtype: int
    """

    config_path, toml_config = _load_config()

    value = toml_config.pop(name, None)
    if value is None:
        emitter.publish(
            errors.DefaultError(
                "Property {!r} doesn't exist".format(name)))
        return 1
    elif isinstance(value, collections.Mapping):
        emitter.publish(_generate_choice_msg(name, value))
        return 1

    _save_config_file(config_path, toml_config)

    return 0


def _show(name):
    """
    :returns: process status
    :rtype: int
    """

    _, toml_config = _load_config()

    if name is not None:
        value = toml_config.get(name)
        if value is None:
            emitter.publish(
                errors.DefaultError(
                    "Property {!r} doesn't exist".format(name)))
            return 1
        elif isinstance(value, collections.Mapping):
            emitter.publish(_generate_choice_msg(name, value))
            return 1
        else:
            emitter.publish(value)
    else:
        # Let's list all of the values
        for key, value in sorted(toml_config.property_items()):
            emitter.publish('{}={}'.format(key, value))

    return 0


def _generate_choice_msg(name, value):
    """
    :param name: name of the property
    :type name: str
    :param value: dictionary for the value
    :type value: dcos.api.config.Toml
    :returns: an error message for top level properties
    :rtype: dcos.api.errors.Error
    """

    message = ("Property {!r} doesn't fully specify a value - "
               "possible properties are:").format(name)
    for key, _ in sorted(value.property_items()):
        message += '\n{}.{}'.format(name, key)

    return errors.DefaultError(message)


def _load_config():
    """
    :returns: process status
    :rtype: int
    """

    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    return (config_path, config.mutable_load_from_path(config_path))


def _save_config_file(config_path, toml_config):
    """
    :param config_path: path to configuration file.
    :type config_path: str
    :param toml_config: TOML configuration object
    :type toml_config: MutableToml or Toml
    """

    serial = toml.dumps(toml_config._dictionary)
    with open(config_path, 'w') as config_file:
        config_file.write(serial)
