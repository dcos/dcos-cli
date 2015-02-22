"""
Usage:
    dcos config info
    dcos config <name> [<value>]
    dcos config --unset <name>
    dcos config --list

Options:
    -h, --help            Show this screen
    --version             Show version
    --unset               Remove property from the config file
"""

import collections
import os

import docopt
import toml
from dcos.api import config, constants, emitting, options, util

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    args = docopt.docopt(
        __doc__,
        version='dcos-config version {}'.format(constants.version))

    if args['config'] and args['info']:
        emitter.publish('Get and set DCOS command line options')

    elif args['config'] and args['--unset']:
        toml_config = config.mutable_load_from_path(config_path)
        if toml_config.pop(args['<name>'], None):
            _save_config_file(config_path, toml_config)

    elif args['config'] and args['--list']:
        toml_config = config.load_from_path(config_path)
        for key, value in sorted(toml_config.property_items()):
            emitter.publish('{}={}'.format(key, value))

    elif args['config'] and args['<value>'] is None:
        toml_config = config.load_from_path(config_path)
        value = toml_config.get(args['<name>'])
        if value is not None and not isinstance(value, collections.Mapping):
            emitter.publish(value)
        else:
            return 1

    elif args['config']:
        toml_config = config.mutable_load_from_path(config_path)
        toml_config[args['<name>']] = args['<value>']
        _save_config_file(config_path, toml_config)

    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return 0


def _save_config_file(config_path, toml_config):
    """Save dictionary as TOML file

    :param config_path: Path to configuration file.
    :type config_path: str or unicode
    """

    serial = toml.dumps(toml_config._dictionary)
    with open(config_path, 'w') as config_file:
        config_file.write(serial)
