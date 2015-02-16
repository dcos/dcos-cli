"""
Usage:
    dcos marathon describe [--json] <app_id>
    dcos marathon info
    dcos marathon list
    dcos marathon remove [--force] <app_id>
    dcos marathon scale [--force] <app_id> <instances>
    dcos marathon start <app_resource>
    dcos marathon suspend [--force] <app_id>

Options:
    -h, --help          Show this screen
    --version           Show version
    --force             This flag disable checks in Marathon during update
                        operations.
    --json              Outputs JSON format instead of default (TOML) format
"""

import json
import os

import docopt
import toml
from dcos.api import config, constants, marathon, options, util


def main():
    error = util.configure_logger_from_environ()
    if error is not None:
        print(error.error())
        return 1

    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    args = docopt.docopt(
        __doc__,
        version='dcos-marathon version {}'.format(constants.version))

    if args['marathon'] and args['info']:
        return _info()
    elif args['marathon'] and args['list']:
        toml_config = config.load_from_path(config_path)
        return _list(toml_config)
    elif args['marathon'] and args['describe']:
        toml_config = config.load_from_path(config_path)
        return _describe(args['<app_id>'], args['--json'], toml_config)
    elif args['marathon'] and args['start']:
        toml_config = config.load_from_path(config_path)
        return _start(args['<app_resource>'], toml_config)
    elif args['marathon'] and args['scale']:
        toml_config = config.load_from_path(config_path)
        return _scale(args['<app_id>'],
                      args['<instances>'],
                      args['--force'],
                      toml_config)
    elif args['marathon'] and args['suspend']:
        toml_config = config.load_from_path(config_path)
        return _suspend(args['<app_id>'], args['--force'], toml_config)
    elif args['marathon'] and args['remove']:
        toml_config = config.load_from_path(config_path)
        return _remove(args['<app_id>'], args['--force'], toml_config)
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


def _list(config):
    """Lists known Marathon applications.

    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = marathon.create_client(config)

    apps, err = client.get_apps()
    if err is not None:
        print(err.error())
        return 1

    if not apps:
        print("No applications to list.")

    for app in apps:
        print(app['id'])

    return 0


def _describe(app_id, is_json, config):
    """Show details of a Marathon application.

    :param app_id: ID of the app to suspend
    :type app_id: str
    :param is_json: Whether to print in JSON format or TOML
    :type is_json: bool
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = marathon.create_client(config)

    app, err = client.get_app(app_id)
    if err is not None:
        print(err.error())
        return 1

    if is_json:
        print(json.dumps(app, sort_keys=True, indent=2))
    else:
        print(toml.dumps(app))

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
    client = marathon.create_client(config)

    with open(app_resource_path) as app_resource_file:
        _, err = client.add_app(app_resource_file)
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
    :param force: Whether to override running deployments.
    :type force: bool
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = marathon.create_client(config)

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
    :param force: Whether to override running deployments.
    :type force: bool
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = marathon.create_client(config)

    deployment, err = client.stop_app(app_id, force)
    if err is not None:
        print(err.error())
        return 1

    print('Created deployment {}'.format(deployment))

    return 0


def _remove(app_id, force, config):
    """Remove a Marathon application.

    :param app_id: ID of the app to remove
    :type app_id: str
    :param force: Whether to override running deployments.
    :type force: bool
    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """
    client = marathon.create_client(config)

    err = client.remove_app(app_id, force)
    if err is not None:
        print(err.error())
        return 1

    return 0
