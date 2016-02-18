import collections
import copy

import dcoscli
import docopt
import pkg_resources
from dcos import cmds, config, emitting, http, jsonitem, util
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
        _doc(),
        version='dcos-config version {}'.format(dcoscli.version))

    http.silence_requests_warnings()

    return cmds.execute(_cmds(), args)


def _doc():
    """
    :rtype: str
    """
    return pkg_resources.resource_string(
        'dcoscli',
        'data/help/config.txt').decode('utf-8')


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

    emitter.publish(_doc().split('\n')[0])
    return 0


def _set(name, value):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = config.set_val(name, value)
    if (name == 'core.reporting' is True) or (name == 'core.email'):
        analytics.segment_identify(toml_config)

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

    config.check_config(toml_config_pre, toml_config)

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
    config.check_config(toml_config_pre, toml_config)

    config.save(toml_config)
    return 0


def _unset(name, index):
    """
    :returns: process status
    :rtype: int
    """

    config.unset(name, index)
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
            raise DCOSException(config.generate_choice_msg(name, value))
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
                              config.generate_root_schema(toml_config))
    if len(errs) != 0:
        emitter.publish(util.list_to_err(errs))
        return 1

    emitter.publish("Congratulations, your configuration is valid!")
    return 0


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

    section, subkey = config.split_key(name)

    config_schema = config.get_config_schema(section)

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
