"""
Usage:
    dcos marathon info
    dcos marathon start <app_resource>
    dcos marathon --help
    dcos marathon --version

Options:
    -h, --help          Show this screen
    --version           Show version
"""

import os

import docopt

from .. import config, constants, marathon


def main():
    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    args = docopt.docopt(
        __doc__,
        version='dcos-marathon version {}'.format(constants.version))

    if args['marathon'] and args['info']:
        return _info()
    elif args['marathon'] and args['start']:
        toml_config = config.Toml.load_from_path(config_path)
        return _start(args['<app_resource>'], toml_config)
    else:
        print('Unknown options')
        print(__doc__)
        return 1


def _info():
    """Print marathon cli information

    :returns: Process status
    :rtype: int
    """

    print('Deploy and manage containers for Mesos')
    return 0


def _start(app_resource_path, config):
    """Starts an application with Marathon

    :param app_resource_path: Path to the application resource
    :type app_resource_path: str
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = marathon.Client(config['marathon.host'], config['marathon.port'])

    with open(app_resource_path) as app_resource_file:
        success, err = client.start_app(app_resource_file)
        if err is not None:
            print(err.error())
            return 1

    return 0
