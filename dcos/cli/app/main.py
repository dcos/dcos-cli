"""
Usage:
    dcos app add
    dcos app info
    dcos app list
    dcos app remove [--force] <app-id>

Options:
    -h, --help          Show this screen
    --version           Show version
    --force             This flag disable checks in Marathon during update
                        operations.
"""
import os
import sys

import docopt
from dcos.api import config, constants, marathon, util

logger = util.get_logger(__name__)


def main():
    error = util.configure_logger_from_environ()
    if error is not None:
        print(error.error())
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-app version {}'.format(constants.version))

    if args['app'] and args['info']:
        return _info()

    if args['app'] and args['add']:
        return _add()

    if args['app'] and args['list']:
        return _list()

    if args['app'] and args['remove']:
        return _remove(args['<app-id>'], args['--force'])


def _info():
    """
    :returns: Process status
    :rtype: int
    """

    print('Deploy and manage applications on Apache Mesos')
    return 0


def _add():
    """
    :returns: Process status
    :rtype: int
    """

    # Check that stdin is not tty
    if sys.stdin.isatty():
        # We don't support TTY right now. In the future we will start an editor
        print("We currently don't support reading from the TTY. Please "
              "specify an application JSON.")
        print("E.g. dcos app add < app_resource.json")
        return 1

    application_resource, err = util.load_jsons(sys.stdin.read())
    if err is not None:
        print(err.error())
        return 1

    # Add application to marathon
    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))
    err = client.add_app(application_resource)
    if err is not None:
        print(err.error())
        return 1

    return 0


def _list():
    """
    :returns: Process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    apps, err = client.get_apps()
    if err is not None:
        print(err.error())
        return 1

    if not apps:
        print("No applications to list.")

    for app in apps:
        print(app['id'])

    return 0


def _remove(app_id, force):
    """
    :param app_id: ID of the app to remove
    :type app_id: str
    :param force: Whether to override running deployments.
    :type force: bool
    :returns: Process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    err = client.remove_app(app_id, force)
    if err is not None:
        print(err.error())
        return 1

    return 0
