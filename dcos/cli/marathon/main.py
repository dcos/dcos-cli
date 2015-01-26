"""
Usage:
    dcos marathon info
    dcos marathon list
    dcos marathon describe <app_id>
    dcos marathon start <app_resource>
    dcos marathon scale <app_id> <instances> [--force]
    dcos marathon suspend <app_id> [--force]
    dcos marathon remove <app_id>
    dcos marathon --help
    dcos marathon --version

Options:
    -h, --help          Show this screen
    --version           Show version
"""

import json
import os

import docopt
from dcos.api import config, constants, marathon, options


def main():
    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    args = docopt.docopt(
        __doc__,
        version='dcos-marathon version {}'.format(constants.version))

    if args['marathon'] and args['info']:
        return _info()
    elif args['marathon'] and args['list']:
        toml_config = config.Toml.load_from_path(config_path)
        return _list(toml_config)
    elif args['marathon'] and args['describe']:
        toml_config = config.Toml.load_from_path(config_path)
        return _describe(args['<app_id>'], toml_config)
    elif args['marathon'] and args['start']:
        toml_config = config.Toml.load_from_path(config_path)
        return _start(args['<app_resource>'], toml_config)
    elif args['marathon'] and args['scale']:
        toml_config = config.Toml.load_from_path(config_path)
        return _scale(args['<app_id>'],
                      args['<instances>'],
                      args['--force'],
                      toml_config)
    elif args['marathon'] and args['suspend']:
        toml_config = config.Toml.load_from_path(config_path)
        return _suspend(args['<app_id>'], args['--force'], toml_config)
    elif args['marathon'] and args['remove']:
        toml_config = config.Toml.load_from_path(config_path)
        return _remove(args['<app_id>'], toml_config)
    else:
        print(options.make_generic_usage_error(__doc__))
        return 1


def _info():
    """Print marathon cli information.

    :returns: Process status
    :rtype: int
    """

    print('Deploy and manage applications on Apache Mesos')
    return 0


def _create_client(config):
    """Creates a Marathon client with the supplied configuration.

    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Marathon client
    :rtype: dcos.api.marathon.Client
    """
    return marathon.Client(config['marathon.host'], config['marathon.port'])


def _list(config):
    """Lists known Marathon applications.

    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = _create_client(config)

    apps, err = client.get_apps()
    if err is not None:
        print(err.error())
        return 1

    if not apps:
        print("No apps to list.")

    for app in apps:
        print(app['id'])

    return 0


def _describe(app_id, config):
    """Show details of a Marathon applications.

    :param app_id: ID of the app to suspend
    :type app_id: str
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = _create_client(config)

    app, err = client.get_app(app_id)
    if err is not None:
        print(err.error())
        return 1

    print(json.dumps(app,
                     sort_keys=True,
                     indent=2))

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
    client = _create_client(config)

    with open(app_resource_path) as app_resource_file:
        success, err = client.start_app(app_resource_file)
        if err is not None:
            print(err.error())
            return 1

    return 0


def _scale(app_id, instances, force, config):
    """Suspends a running Marathon application.

    :param app_id: ID of the app to suspend
    :type app_id: str
    :param instances: The requested number of instances.
    :type instances: int
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = _create_client(config)

    deployment, err = client.scale_app(app_id, instances, force)
    if err is not None:
        print(err.error())
        return 1

    print('Created deployment {}'.format(deployment))

    return 0


def _suspend(app_id, force, config):
    """Suspends a running Marathon application.

    :param app_id: ID of the app to suspend
    :type app_id: str
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = _create_client(config)

    deployment, err = client.suspend_app(app_id, force)
    if err is not None:
        print(err.error())
        return 1

    print('Created deployment {}'.format(deployment))

    return 0


def _remove(app_id, config):
    """Remove a Marathon application.

    :param app_id: ID of the app to remove
    :type app_id: str
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = _create_client(config)

    success, err = client.remove_app(app_id)
    if err is not None:
        print(err.error())
        return 1

    return 0
