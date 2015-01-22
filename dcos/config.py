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


def main():
    config_path = os.environ['DCOS_CONFIG']
    args = docopt.docopt(__doc__)

    if args['config'] and args['info']:
        print('Get and set DCOS command line options')

    elif args['config'] and args['--unset']:
        config = _load_config_file(config_path)
        _unset_property(config, args['<name>'])
        _save_config_file(config_path, config)

    elif args['config'] and args['<value>'] is None:
        config = _load_config_file(config_path)
        print(_get_property(config, args['<name>']))

    elif args['config']:
        config = _load_config_file(config_path)
        _set_property(config, args['<name>'], args['<value>'])
        _save_config_file(config_path, config)

    else:
        print(args)


def _load_config_file(config_path):
    with open(config_path) as config_file:
        return toml.loads(config_file.read())


def _save_config_file(config_path, config):
    serial = toml.dumps(config)
    with open(config_path, 'w') as config_file:
        config_file.write(serial)


def _get_property(config, name):
    for section in name.split('.'):
        config = config[section]

    # TODO: Do we want to check that config is not a dictionary?
    return config


def _set_property(config, name, value):
    sections = name.split('.')
    for section in sections[:-1]:
        config = config[section]

    config[sections[-1]] = value


def _unset_property(config, name):
    sections = name.split('.')
    for section in sections[:-1]:
        config = config[section]

    del config[sections[-1]]
