import collections
import copy
import json

import pkg_resources
import six
import toml
from dcos import emitting, jsonitem, subcommand, util
from dcos.errors import DCOSException

emitter = emitting.FlatEmitter()

logger = util.get_logger(__name__)


def set_val(name, value):
    """
    :param name: name of paramater
    :type name: str
    :param value: value to set to paramater `name`
    :type param: str
    :returns: Toml config
    :rtype: Toml
    """

    toml_config = util.get_config(True)

    section, subkey = split_key(name)

    config_schema = get_config_schema(section)

    new_value = jsonitem.parse_json_value(subkey, value, config_schema)

    toml_config_pre = copy.deepcopy(toml_config)
    if section not in toml_config_pre._dictionary:
        toml_config_pre._dictionary[section] = {}

    value_exists = name in toml_config
    old_value = toml_config.get(name)

    toml_config[name] = new_value

    check_config(toml_config_pre, toml_config)

    save(toml_config)

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

    return toml_config


def unset(name, index):
    """
    :param name: name of paramater
    :type name: str
    :param index: index in list to unset
    :type param: int
    :rtype: None
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
        raise DCOSException(generate_choice_msg(name, value))
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
        save(toml_config)
        return
    elif index is not None:
        raise DCOSException(
            'Unsetting based on an index is only supported for lists')
    else:
        emitter.publish("Removed [{}]".format(name))
        save(toml_config)
        return


def load_from_path(path, mutable=False):
    """Loads a TOML file from the path

    :param path: Path to the TOML file
    :type path: str
    :param mutable: True if the returned Toml object should be mutable
    :type mutable: boolean
    :returns: Map for the configuration file
    :rtype: Toml | MutableToml
    """

    util.ensure_file_exists(path)
    with util.open_file(path, 'r') as config_file:
        try:
            toml_obj = toml.loads(config_file.read())
        except Exception as e:
            raise DCOSException(
                'Error parsing config file at [{}]: {}'.format(path, e))
        return (MutableToml if mutable else Toml)(toml_obj)


def save(toml_config):
    """
    :param toml_config: TOML configuration object
    :type toml_config: MutableToml or Toml
    """

    serial = toml.dumps(toml_config._dictionary)
    path = util.get_config_path()
    with util.open_file(path, 'w') as config_file:
        config_file.write(serial)


def _get_path(toml_config, path):
    """
    :param config: Dict with the configuration values
    :type config: dict
    :param path: Path to the value. E.g. 'path.to.value'
    :type path: str
    :returns: Value stored at the given path
    :rtype: double, int, str, list or dict
    """

    for section in path.split('.'):
        toml_config = toml_config[section]

    return toml_config


def _iterator(parent, dictionary):
    """
    :param parent: Path to the value parameter
    :type parent: str
    :param dictionary: Value of the key
    :type dictionary: collection.Mapping
    :returns: An iterator of tuples for each property and value
    :rtype: iterator of (str, any) where any can be str, int, double, list
    """

    for key, value in dictionary.items():

        new_key = key
        if parent is not None:
            new_key = "{}.{}".format(parent, key)

        if not isinstance(value, collections.Mapping):
            yield (new_key, value)
        else:
            for x in _iterator(new_key, value):
                yield x


def split_key(name):
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


def get_config_schema(command):
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
                'dcos',
                'data/config-schema/core.json').decode('utf-8'))

    executable = subcommand.command_executables(command)
    return subcommand.config_schema(executable)


def check_config(toml_config_pre, toml_config_post):
    """
    :param toml_config_pre: dictionary for the value before change
    :type toml_config_pre: dcos.api.config.Toml
    :param toml_config_post: dictionary for the value with change
    :type toml_config_post: dcos.api.config.Toml
    :returns: process status
    :rtype: int
    """

    errors_pre = util.validate_json(toml_config_pre._dictionary,
                                    generate_root_schema(toml_config_pre))
    errors_post = util.validate_json(toml_config_post._dictionary,
                                     generate_root_schema(toml_config_post))

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


def generate_choice_msg(name, value):
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


def generate_root_schema(toml_config):
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
        config_schema = get_config_schema(section)
        root_schema['properties'][section] = config_schema

    return root_schema


class Toml(collections.Mapping):
    """Class for getting value from TOML.

    :param dictionary: configuration dictionary
    :type dictionary: dict
    """

    def __init__(self, dictionary):
        self._dictionary = dictionary

    def __getitem__(self, path):
        """
        :param path: Path to the value. E.g. 'path.to.value'
        :type path: str
        :returns: Value stored at the given path
        :rtype: double, int, str, list or dict
        """

        toml_config = _get_path(self._dictionary, path)
        if isinstance(toml_config, collections.Mapping):
            return Toml(toml_config)
        else:
            return toml_config

    def __iter__(self):
        """
        :returns: Dictionary iterator
        :rtype: iterator
        """

        return iter(self._dictionary)

    def property_items(self):
        """Iterator for full-path keys and values

        :returns: Iterator for pull-path keys and values
        :rtype: iterator of tuples
        """

        return _iterator(None, self._dictionary)

    def __len__(self):
        """
        :returns: The length of the dictionary
        :rtype: int
        """

        return len(self._dictionary)


class MutableToml(collections.MutableMapping):
    """Class for managing CLI configuration through TOML.

    :param dictionary: configuration dictionary
    :type dictionary: dict
    """

    def __init__(self, dictionary):
        self._dictionary = dictionary

    def __getitem__(self, path):
        """
        :param path: Path to the value. E.g. 'path.to.value'
        :type path: str
        :returns: Value stored at the given path
        :rtype: double, int, str, list or dict
        """

        toml_config = _get_path(self._dictionary, path)
        if isinstance(toml_config, collections.MutableMapping):
            return MutableToml(toml_config)
        else:
            return toml_config

    def __iter__(self):
        """
        :returns: Dictionary iterator
        :rtype: iterator
        """

        return iter(self._dictionary)

    def property_items(self):
        """Iterator for full-path keys and values

        :returns: Iterator for pull-path keys and values
        :rtype: iterator of tuples
        """

        return _iterator(None, self._dictionary)

    def __len__(self):
        """
        :returns: The length of the dictionary
        :rtype: int
        """

        return len(self._dictionary)

    def __setitem__(self, path, value):
        """
        :param path: Path to set
        :type path: str
        :param value: Value to store
        :type value: double, int, str, list or dict
        """

        toml_config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            toml_config = toml_config.setdefault(section, {})

        toml_config[sections[-1]] = value

    def __delitem__(self, path):
        """
        :param path: Path to delete
        :type path: str
        """
        toml_config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            toml_config = toml_config[section]

        del toml_config[sections[-1]]
