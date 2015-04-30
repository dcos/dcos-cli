import collections

import toml


def mutable_load_from_path(path):
    """Loads a TOML file from the path

    :param path: Path to the TOML file
    :type path: str
    :returns: Mutable map for the configuration file
    :rtype: MutableToml
    """

    with open(path) as config_file:
        return MutableToml(toml.loads(config_file.read()))


def load_from_path(path):
    """Loads a TOML file from the path

    :param path: Path to the TOML file
    :type path: str
    :returns: Map for the configuration file
    :rtype: Toml
    """

    with open(path) as config_file:
        return Toml(toml.loads(config_file.read()))


def _get_path(config, path):
    """
    :param config: Dict with the configuration values
    :type config: dict
    :param path: Path to the value. E.g. 'path.to.value'
    :type path: str
    :returns: Value stored at the given path
    :rtype: double, int, str, list or dict
    """

    for section in path.split('.'):
        config = config[section]

    return config


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

        config = _get_path(self._dictionary, path)
        if isinstance(config, collections.Mapping):
            return Toml(config)
        else:
            return config

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

        config = _get_path(self._dictionary, path)
        if isinstance(config, collections.MutableMapping):
            return MutableToml(config)
        else:
            return config

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

        config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            config = config.setdefault(section, {})

        config[sections[-1]] = value

    def __delitem__(self, path):
        """
        :param path: Path to delete
        :type path: str
        """
        config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            config = config[section]

        del config[sections[-1]]
