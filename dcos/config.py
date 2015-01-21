import collections

import toml


class Toml(collections.MutableMapping):

    """Class for managing CLI configuration through TOML."""

    def __init__(self, dictionary):
        """Constructs interface for managing configurations

        :config_path: (string) Path to the TOML configuration file

        """
        self._dictionary = dictionary

    def __getitem__(self, path):
        config = self._dictionary

        for section in path.split('.'):
            config = config[section]

        if isinstance(config, collections.MutableMapping):
            return Toml(config)
        else:
            return config

    def __iter__(self):
        return iter(self._dictionary)

    def __len__(self):
        return len(self._dictionary)

    def __setitem__(self, path, value):
        config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            config = config[section]

        config[sections[-1]] = value

    def __delitem__(self, path):
        config = self._dictionary

        sections = path.split('.')
        for section in sections[:-1]:
            config = config[section]

        del config[sections[-1]]

    @classmethod
    def load_from_path(class_, path):
        with open(path) as config_file:
            return Toml(toml.loads(config_file.read()))
