"""
Usage:
    dcos config info
    dcos config <name> [<value>]
    dcos config --unset <name>
    dcos config --help

Options:
    -h, --help            Show this screen
    --unset               Remove property from the config file
"""

import os

import docopt
import toml
from dcos.api import config, constants


def main():
    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    args = docopt.docopt(
        __doc__,
        version='dcos-config version {}'.format(constants.version))

    if args['config'] and args['info']:
        print('Get and set DCOS command line options')

    elif args['config'] and args['--unset']:
        toml_config = config.Toml.load_from_path(config_path)
        del toml_config[args['<name>']]
        _save_config_file(config_path, toml_config)

    elif args['config'] and args['<value>'] is None:
        toml_config = config.Toml.load_from_path(config_path)
        print(toml_config[args['<name>']])

    elif args['config']:
        toml_config = config.Toml.load_from_path(config_path)
        toml_config[args['<name>']] = args['<value>']
        _save_config_file(config_path, toml_config)

    else:
        print(args)


def _save_config_file(config_path, toml_config):
    """Save dictionary as TOML file

    :param config_path: Path to configuration file.
    :type config_path: str or unicode
    """

    serial = toml.dumps(toml_config)
    with open(config_path, 'w') as config_file:
        config_file.write(serial)
