import collections

import toml


class Toml(collections.MutableMapping):

    """Class for managing CLI configuration through TOML."""

    def __init__(self, dictionary):
        """Constructs interface for managing configurations

        :param dictionary: Configuration dictionary
        :type dictionary: dict
        """

        self._dictionary = dictionary

    def __getitem__(self, path):
        """Get the value for a path

        :param path: Path to the value. E.g. 'path.to.value'
        :type path: str
        :returns: Value stored at the given path
        :rtype: double, int, str, list or dict
        """

        config = self._dictionary

        for section in path.split('.'):
            config = config[section]

        if isinstance(config, collections.MutableMapping):
            return Toml(config)
        else:
            return config

    def __iter__(self):
        """Returns iterator

        :returns: Dictionary iterator
        :rtype: iterator
        """

        return iter(self._dictionary)

    def __len__(self):
        """Length of the toml configuration

        :returns: The length of the dictionary
        :rtype: int
        """

        return len(self._dictionary)

    def __setitem__(self, path, value):
        """Set the path to a value

        :param path: Path to set
        :type path: str
        :param value: Value to store
        :type value: double, int, str, list or dict
        """

        config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            config = config[section]

        config[sections[-1]] = value

    def __delitem__(self, path):
        """Delete value stored at path

        :param path: Path to delete
        :type path: str
        """
        config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            config = config[section]

        del config[sections[-1]]

    @classmethod
    def load_from_path(class_, path):
        """Loads a TOML file from the path

        :param path: Path to the TOML file
        :type path: str
        :returns: Dictionary for the configuration file
        :rtype: Toml
        """

        with open(path) as config_file:
            return Toml(toml.loads(config_file.read()))
