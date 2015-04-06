"""Get and set DCOS command line options

Usage:
    dcos config --info
    dcos config append <name> <value>
    dcos config prepend <name> <value>
    dcos config set <name> <value>
    dcos config show [<name>]
    dcos config unset [--index=<index>] <name>
    dcos config validate

Options:
    -h, --help       Show this screen
    --info           Show a short description of this subcommand
    --version        Show version
    --index=<index>  Index into the list. The first element in the list has an
                     index of zero

Positional Arguments:
    <name>           The name of the property
    <value>          The value of the property
"""

import collections
import os

import dcoscli
import docopt
import six
import toml
from dcos.api import (cmds, config, constants, emitting, errors, jsonitem,
                      options, subcommand, util)

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-config version {}'.format(dcoscli.version))

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
            hierarchy=['config', 'set'],
            arg_keys=['<name>', '<value>'],
            function=_set),

        cmds.Command(
            hierarchy=['config', 'append'],
            arg_keys=['<name>', '<value>'],
            function=_append),

        cmds.Command(
            hierarchy=['config', 'prepend'],
            arg_keys=['<name>', '<value>'],
            function=_prepend),

        cmds.Command(
            hierarchy=['config', 'unset'],
            arg_keys=['<name>', '--index'],
            function=_unset),

        cmds.Command(
            hierarchy=['config', 'show'],
            arg_keys=['<name>'],
            function=_show),

        cmds.Command(
            hierarchy=['config', 'validate'],
            arg_keys=[],
            function=_validate),

        cmds.Command(
            hierarchy=['config'],
            arg_keys=['--info'],
            function=_info),
    ]


def _info(info):
    """
    :param info: Whether to output a description of this subcommand
    :type info: boolean
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

    section, subkey = _split_key(name)

    config_schema, err = _get_config_schema(section)
    if err is not None:
        emitter.publish(err)
        return 1

    python_value, err = jsonitem.parse_json_value(subkey, value, config_schema)
    if err is not None:
        emitter.publish(err)
        return 1

    toml_config[name] = python_value
    _save_config_file(config_path, toml_config)

    return 0


def _append(name, value):
    """
    :returns: process status
    :rtype: int
    """

    config_path, toml_config = _load_config()

    python_value, err = _parse_array_item(name, value)
    if err is not None:
        emitter.publish(err)
        return 1

    toml_config[name] = toml_config.get(name, []) + python_value
    _save_config_file(config_path, toml_config)

    return 0


def _prepend(name, value):
    """
    :returns: process status
    :rtype: int
    """

    config_path, toml_config = _load_config()

    python_value, err = _parse_array_item(name, value)
    if err is not None:
        emitter.publish(err)
        return 1

    toml_config[name] = python_value + toml_config.get(name, [])
    _save_config_file(config_path, toml_config)

    return 0


def _unset(name, index):
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
    elif (isinstance(value, collections.Sequence) and
          not isinstance(value, six.string_types)):
        if index is not None:
            index, err = util.parse_int(index)
            if err is not None:
                emitter.publish(err)
                return 1

            if index < 0 or index >= len(value):
                emitter.publish(
                    errors.DefaultError(
                        'Index ({}) is out of bounds - possible values are '
                        'between {} and {}'.format(index, 0, len(value) - 1)))
                return 1

            value.pop(index)
            toml_config[name] = value
    elif index is not None:
        emitter.publish(
            errors.DefaultError(
                'Unsetting based on an index is only supported for lists'))
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


def _validate():
    """
    :returns: process status
    :rtype: int
    """

    _, toml_config = _load_config()

    root_schema = {
        '$schema': 'http://json-schema.org/schema#',
        'type': 'object',
        'properties': {},
        'additionalProperties': False,
    }

    # Load the config schema from all the subsections into the root schema
    for section in toml_config.keys():
        config_schema, err = _get_config_schema(section)
        if err is not None:
            emitter.publish(err)
            return 1

        root_schema['properties'][section] = config_schema

    err = util.validate_json(toml_config._dictionary, root_schema)
    if err is not None:
        emitter.publish(err)
        return 1

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


def _get_config_schema(command):
    """
    :param command: the subcommand name
    :type command: str
    :returns: the subcommand's configuration schema
    :rtype: (dict, dcos.api.errors.Error)
    """

    executable, err = subcommand.command_executables(
        command,
        util.dcos_path())
    if err is not None:
        return (None, err)

    return (subcommand.config_schema(executable), None)


def _split_key(name):
    """
    :param name: the full property path - e.g. marathon.host
    :type name: str
    :returns: the section and property name
    :rtype: ((str, str), Error)
    """

    terms = name.split('.', 1)
    if len(terms) != 2:
        emitter.publish(
            errors.DefaultError('Property name must have both a section and '
                                'key: <section>.<key> - E.g. marathon.host'))
        return 1

    return (terms[0], terms[1])


def _parse_array_item(name, value):
    """
    :param name: the name of the property
    :type name: str
    :param value: the value to parse
    :type value: str
    :returns: the parsed value as an array with one element
    :rtype: (list of any, dcos.api.errors.Error) where any is string, int,
            float, bool, array or dict
    """

    section, subkey = _split_key(name)

    config_schema, err = _get_config_schema(section)
    if err is not None:
        return (None, err)

    parser, err = jsonitem.find_parser(subkey, config_schema)
    if err is not None:
        return (None, err)

    if parser.schema['type'] != 'array':
        return (
            None,
            errors.DefaultError(
                "Append/Prepend not supported on '{0}' properties - use 'dcos "
                "config set {0} {1}'".format(name, value))
        )

    if ('items' in parser.schema and
       parser.schema['items']['type'] == 'string'):

        value = '["' + value + '"]'
    else:
        # We are going to assume that wrapping it in an array is enough
        value = '[' + value + ']'

    return parser(value)
