"""Get and set DCOS CLI configuration properties

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
import copy
import json

import dcoscli
import docopt
import pkg_resources
import six
from dcos import cmds, config, emitting, http, jsonitem, subcommand, util
from dcos.errors import DCOSException
from dcoscli import analytics
from dcoscli.main import decorate_docopt_usage

emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main():
    util.configure_process_from_environ()

    args = docopt.docopt(
        __doc__,
        version='dcos-config version {}'.format(dcoscli.version))

    http.silence_requests_warnings()

    return cmds.execute(_cmds(), args)


def _check_config(toml_config_pre, toml_config_post):
    """
    :param toml_config_pre: dictionary for the value before change
    :type toml_config_pre: dcos.api.config.Toml
    :param toml_config_post: dictionary for the value with change
    :type toml_config_post: dcos.api.config.Toml
    :returns: process status
    :rtype: int
    """

    errors_pre = util.validate_json(toml_config_pre._dictionary,
                                    _generate_root_schema(toml_config_pre))
    errors_post = util.validate_json(toml_config_post._dictionary,
                                     _generate_root_schema(toml_config_post))

    logger.info('Comparing changes in the configuration...')
    logger.info('Errors before the config command: %r', errors_pre)
    logger.info('Errors after the config command: %r', errors_post)

    if len(errors_post) != 0:
        if len(errors_pre) == 0:
            raise DCOSException(util.list_to_err(errors_post))

        def _errs(errs):
            return set([e.split('\n')[0] for e in errs])

        diff_errors = _errs(errors_post) - _errs(errors_pre)
        if len(diff_errors) != 0:
            raise DCOSException(util.list_to_err(errors_post))


def _cmds():
    """
    :returns: all the supported commands
    :rtype: list of dcos.cmds.Command
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

    toml_config = util.get_config(True)

    section, subkey = _split_key(name)

    config_schema = _get_config_schema(section)

    new_value = jsonitem.parse_json_value(subkey, value, config_schema)

    toml_config_pre = copy.deepcopy(toml_config)
    if section not in toml_config_pre._dictionary:
        toml_config_pre._dictionary[section] = {}

    value_exists = name in toml_config
    old_value = toml_config.get(name)

    toml_config[name] = new_value

    if (name == 'core.reporting' and new_value is True) or \
       (name == 'core.email'):
        analytics.segment_identify(toml_config)

    _check_config(toml_config_pre, toml_config)

    config.save(toml_config)

    if not value_exists:
        emitter.publish("[{}]: set to '{}'".format(name, new_value))
    elif old_value == new_value:
        emitter.publish("[{}]: already set to '{}'".format(name, old_value))
    else:
        emitter.publish(
            "[{}]: changed from '{}' to '{}'".format(
                name,
                old_value,
                new_value))
    return 0


def _append(name, value):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = util.get_config(True)

    python_value = _parse_array_item(name, value)
    toml_config_pre = copy.deepcopy(toml_config)
    section = name.split(".", 1)[0]
    if section not in toml_config_pre._dictionary:
        toml_config_pre._dictionary[section] = {}

    toml_config[name] = toml_config.get(name, []) + python_value

    _check_config(toml_config_pre, toml_config)

    config.save(toml_config)
    return 0


def _prepend(name, value):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = util.get_config(True)

    python_value = _parse_array_item(name, value)

    toml_config_pre = copy.deepcopy(toml_config)
    section = name.split(".", 1)[0]
    if section not in toml_config_pre._dictionary:
        toml_config_pre._dictionary[section] = {}
    toml_config[name] = python_value + toml_config.get(name, [])
    _check_config(toml_config_pre, toml_config)

    config.save(toml_config)
    return 0


def _unset(name, index):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = util.get_config(True)
    toml_config_pre = copy.deepcopy(toml_config)
    section = name.split(".", 1)[0]
    if section not in toml_config_pre._dictionary:
        toml_config_pre._dictionary[section] = {}
    value = toml_config.pop(name, None)
    if value is None:
        raise DCOSException("Property {!r} doesn't exist".format(name))
    elif isinstance(value, collections.Mapping):
        raise DCOSException(_generate_choice_msg(name, value))
    elif ((isinstance(value, collections.Sequence) and
           not isinstance(value, six.string_types)) and
          index is not None):
        index = util.parse_int(index)

        if not value:
            raise DCOSException(
                'Index ({}) is out of bounds - [{}] is empty'.format(
                    index,
                    name))
        if index < 0 or index >= len(value):
            raise DCOSException(
                'Index ({}) is out of bounds - possible values are '
                'between {} and {}'.format(index, 0, len(value) - 1))

        popped_value = value.pop(index)
        emitter.publish(
            "[{}]: removed element '{}' at index '{}'".format(
                name, popped_value, index))

        toml_config[name] = value
        config.save(toml_config)
        return 0
    elif index is not None:
        raise DCOSException(
            'Unsetting based on an index is only supported for lists')
    else:
        emitter.publish("Removed [{}]".format(name))
        config.save(toml_config)
        return 0


def _show(name):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = util.get_config(True)

    if name is not None:
        value = toml_config.get(name)
        if value is None:
            raise DCOSException("Property {!r} doesn't exist".format(name))
        elif isinstance(value, collections.Mapping):
            raise DCOSException(_generate_choice_msg(name, value))
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

    toml_config = util.get_config(True)

    errs = util.validate_json(toml_config._dictionary,
                              _generate_root_schema(toml_config))
    if len(errs) != 0:
        emitter.publish(util.list_to_err(errs))
        return 1

    emitter.publish("Congratulations, your configuration is valid!")
    return 0


def _generate_root_schema(toml_config):
    """
    :param toml_configs: dictionary of values
    :type toml_config: TomlConfig
    :returns: configuration_schema
    :rtype: jsonschema
    """

    root_schema = {
        '$schema': 'http://json-schema.org/schema#',
        'type': 'object',
        'properties': {},
        'additionalProperties': False,
    }

    # Load the config schema from all the subsections into the root schema
    for section in toml_config.keys():
        config_schema = _get_config_schema(section)
        root_schema['properties'][section] = config_schema

    return root_schema


def _generate_choice_msg(name, value):
    """
    :param name: name of the property
    :type name: str
    :param value: dictionary for the value
    :type value: dcos.config.Toml
    :returns: an error message for top level properties
    :rtype: str
    """

    message = ("Property {!r} doesn't fully specify a value - "
               "possible properties are:").format(name)
    for key, _ in sorted(value.property_items()):
        message += '\n{}.{}'.format(name, key)

    return message


def _get_config_schema(command):
    """
    :param command: the subcommand name
    :type command: str
    :returns: the subcommand's configuration schema
    :rtype: dict
    """

    # core.* config variables are special.  They're valid, but don't
    # correspond to any particular subcommand, so we must handle them
    # separately.
    if command == "core":
        return json.loads(
            pkg_resources.resource_string(
                'dcoscli',
                'data/config-schema/core.json').decode('utf-8'))

    executable = subcommand.command_executables(command)
    return subcommand.config_schema(executable)


def _split_key(name):
    """
    :param name: the full property path - e.g. marathon.url
    :type name: str
    :returns: the section and property name
    :rtype: (str, str)
    """

    terms = name.split('.', 1)
    if len(terms) != 2:
        raise DCOSException('Property name must have both a section and '
                            'key: <section>.<key> - E.g. marathon.url')

    return (terms[0], terms[1])


def _parse_array_item(name, value):
    """
    :param name: the name of the property
    :type name: str
    :param value: the value to parse
    :type value: str
    :returns: the parsed value as an array with one element
    :rtype: (list of any, dcos.errors.Error) where any is string, int,
            float, bool, array or dict
    """

    section, subkey = _split_key(name)

    config_schema = _get_config_schema(section)

    parser = jsonitem.find_parser(subkey, config_schema)

    if parser.schema['type'] != 'array':
        raise DCOSException(
            "Append/Prepend not supported on '{0}' properties - use 'dcos "
            "config set {0} {1}'".format(name, value))

    if ('items' in parser.schema and
       parser.schema['items']['type'] == 'string'):

        value = '["' + value + '"]'
    else:
        # We are going to assume that wrapping it in an array is enough
        value = '[' + value + ']'

    return parser(value)
