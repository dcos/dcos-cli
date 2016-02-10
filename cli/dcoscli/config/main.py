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

    toml_config = util.get_config(True)

    section, subkey = config._split_key(name)

    config_schema = config._get_config_schema(section)

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

    config._check_config(toml_config_pre, toml_config)

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

    config.append(name, value)
    return 0


def _prepend(name, value):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = util.get_config(True)

    python_value = config._parse_array_item(name, value)

    toml_config_pre = copy.deepcopy(toml_config)
    section = name.split(".", 1)[0]
    if section not in toml_config_pre._dictionary:
        toml_config_pre._dictionary[section] = {}
    toml_config[name] = python_value + toml_config.get(name, [])
    config._check_config(toml_config_pre, toml_config)

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
            raise DCOSException(config._generate_choice_msg(name, value))
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
                              config._generate_root_schema(toml_config))
    if len(errs) != 0:
        emitter.publish(util.list_to_err(errs))
        return 1

    emitter.publish("Congratulations, your configuration is valid!")
    return 0
