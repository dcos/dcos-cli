"""
Usage:
    dcos app add [<app-resource>]
    dcos app deployment list [<app-id>]
    dcos app deployment rollback <deployment-id>
    dcos app deployment stop <deployment-id>
    dcos app deployment watch [--max-count=<max-count>] [--interval=<interval>]
         <deployment-id>
    dcos app info
    dcos app list
    dcos app remove [--force] <app-id>
    dcos app restart [--force] <app-id>
    dcos app show [--app-version=<app-version>] <app-id>
    dcos app start [--force] <app-id> [<instances>]
    dcos app stop [--force] <app-id>
    dcos app update [--force] <app-id> [<properties>...]
    dcos app version list [--max-count=<max-count>] <app-id>

Options:
    -h, --help                   Show this screen
    --version                    Show version
    --force                      This flag disable checks in Marathon during
                                 update operations.
    --app-version=<app-version>  This flag specifies the application version to
                                 use for the command. The application version
                                 (<app-version>) can be specified as an
                                 absolute value or as relative value. Absolute
                                 version values must be in ISO8601 date format.
                                 Relative values must be specified as a
                                 negative integer and they represent the
                                 version from the currently deployed
                                 application definition.
    --max-count=<max-count>      Maximum number of entries to try to fetch and
                                 return
    --interval=<interval>        Number of seconds to wait between actions

Positional arguments:
    <app-id>                The application id
    <app-resource>          The application resource; for a detailed
                            description see (https://mesosphere.github.io/
                            marathon/docs/rest-api.html#post-/v2/apps)
    <deployment-id>         The deployment id
    <instances>             The number of instances to start
    <properties>            Optional key-value pairs to be included in the
                            command. The separator between the key and value
                            must be the '=' character. E.g. cpus=2.0
"""
import json
import os
import sys
import time

import docopt
import pkg_resources
from dcos.api import (cmds, config, constants, emitting, errors, jsonitem,
                      marathon, options, util)

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-app version {}'.format(constants.version))

    if not args['app']:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    returncode, err = cmds.execute(_cmds(), args)
    if err is not None:
        emitter.publish(err)
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return returncode


def _cmds():
    """
    :returns: all the supported commands
    :rtype: dcos.api.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['version', 'list'],
            arg_keys=['<app-id>', '--max-count'],
            function=_version_list),

        cmds.Command(
            hierarchy=['deployment', 'list'],
            arg_keys=['<app-id>'],
            function=_deployment_list),

        cmds.Command(
            hierarchy=['deployment', 'rollback'],
            arg_keys=['<deployment-id>'],
            function=_deployment_rollback),

        cmds.Command(
            hierarchy=['deployment', 'stop'],
            arg_keys=['<deployment-id>'],
            function=_deployment_stop),

        cmds.Command(
            hierarchy=['deployment', 'watch'],
            arg_keys=['<deployment-id>', '--max-count', '--interval'],
            function=_deployment_watch),

        cmds.Command(hierarchy=['info'], arg_keys=[], function=_info),

        cmds.Command(
            hierarchy=['add'],
            arg_keys=['<app-resource>'],
            function=_add),

        cmds.Command(hierarchy=['list'], arg_keys=[], function=_list),

        cmds.Command(
            hierarchy=['remove'],
            arg_keys=['<app-id>', '--force'],
            function=_remove),

        cmds.Command(
            hierarchy=['show'],
            arg_keys=['<app-id>', '--app-version'],
            function=_show),

        cmds.Command(
            hierarchy=['start'],
            arg_keys=['<app-id>', '<instances>', '--force'],
            function=_start),

        cmds.Command(
            hierarchy=['stop'],
            arg_keys=['<app-id>', '--force'],
            function=_stop),

        cmds.Command(
            hierarchy=['update'],
            arg_keys=['<app-id>', '<properties>', '--force'],
            function=_update),

        cmds.Command(
            hierarchy=['restart'],
            arg_keys=['<app-id>', '--force'],
            function=_restart),
    ]


def _info():
    """
    :returns: Process status
    :rtype: int
    """

    emitter.publish('Deploy and manage applications on the DCOS')
    return 0


def _add(app_resource):
    """
    :param app_resource: optional filename for the application resource
    :type app_resource: str
    :returns: Process status
    :rtype: int
    """

    if app_resource is not None:
        with open(app_resource) as fd:
            application_resource, err = util.load_json(fd)
    else:
        # Check that stdin is not tty
        if sys.stdin.isatty():
            # We don't support TTY right now. In the future we will start an
            # editor
            emitter.publish(
                "We currently don't support reading from the TTY. Please "
                "specify an application JSON.\n"
                "E.g. dcos app add < app_resource.json")
            return 1

        application_resource, err = util.load_json(sys.stdin)

    if err is not None:
        emitter.publish(err)
        return 1

    schema = json.loads(
        pkg_resources.resource_string(
            'dcos',
            'data/marathon-schema.json').decode('utf-8'))

    err = util.validate_json(application_resource, schema)
    if err is not None:
        emitter.publish(err)
        return 1

    # Add application to marathon
    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    # Check that the application doesn't exist
    app_id = marathon.normalize_app_id(application_resource['id'])
    app, err = client.get_app(app_id)
    if app is not None:
        emitter.publish("Application '{}' already exists".format(app_id))
        return 1

    _, err = client.add_app(application_resource)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _list():
    """
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    apps, err = client.get_apps()
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish(apps)

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
        emitter.publish(err)
        return 1

    return 0


def _show(app_id, version):
    """Show details of a Marathon application.

    :param app_id: The id for the application
    :type app_id: str
    :param version: The version, either absolute (date-time) or relative
    :type version: str
    :returns: Process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    if version is not None:
        version, err = _calculate_version(client, app_id, version)
        if err is not None:
            emitter.publish(err)
            return 1

    app, err = client.get_app(app_id, version=version)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish(app)

    return 0


def _start(app_id, instances, force):
    """Start a Marathon application.

    :param app_id: the id for the application
    :type app_id: str
    :param instances: the number of instances to start
    :type instances: str
    :param force: whether to override running deployments
    :type force: bool
    :returns: Process status
    :rtype: int
    """

    # Check that the application exists
    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    desc, err = client.get_app(app_id)
    if err is not None:
        emitter.publish(err)
        return 1

    if desc['instances'] > 0:
        emitter.publish(
            'Application {!r} already started: {!r} instances.'.format(
                app_id,
                desc['instances']))
        return 1

    schema = json.loads(
        pkg_resources.resource_string(
            'dcos',
            'data/marathon-schema.json').decode('utf-8'))

    app_json = {}

    # Need to add the 'id' because it is required
    app_json['id'] = app_id

    # Set instances to 1 if not specified
    if instances is None:
        instances = 1
    else:
        instances, err = _parse_int(instances)
        if err is not None:
            emitter.publish(err)
            return 1

        if instances <= 0:
            emitter.publish(
                'The number of instances must be positive: {!r}.'.format(
                    instances))
            return 1

    app_json['instances'] = instances

    err = util.validate_json(app_json, schema)
    if err is not None:
        emitter.publish(err)
        return 1

    deployment, err = client.update_app(app_id, app_json, force)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish('Created deployment {}'.format(deployment))

    return 0


def _stop(app_id, force):
    """Stop a Marathon application

    :param app_id: the id of the application
    :type app_id: str
    :param force: whether to override running deployments
    :type force: bool
    :returns: process status
    :rtype: int
    """

    # Check that the application exists
    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    desc, err = client.get_app(app_id)
    if err is not None:
        emitter.publish(err)
        return 1

    if desc['instances'] <= 0:
        emitter.publish(
            'Application {!r} already stopped: {!r} instances.'.format(
                app_id,
                desc['instances']))
        return 1

    app_json = {'instances': 0}

    deployment, err = client.update_app(app_id, app_json, force)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish('Created deployment {}'.format(deployment))


def _update(app_id, json_items, force):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param json_items: json update items
    :type json_items: list of str
    :param force: whether to override running deployments
    :type force: bool
    :returns: process status
    :rtype: int
    """

    # Check that the application exists
    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    _, err = client.get_app(app_id)
    if err is not None:
        emitter.publish(err)
        return 1

    if len(json_items) == 0:
        if sys.stdin.isatty():
            # We don't support TTY right now. In the future we will start an
            # editor
            emitter.publish(
                "We currently don't support reading from the TTY. Please "
                "specify an application JSON.\n"
                "E.g. dcos app update < app_update.json")
            return 1
        else:
            return _update_from_stdin(app_id, force)

    schema = json.loads(
        pkg_resources.resource_string(
            'dcos',
            'data/marathon-schema.json').decode('utf-8'))

    app_json = {}

    # Need to add the 'id' because it is required
    app_json['id'] = app_id

    for json_item in json_items:
        key_value, err = jsonitem.parse_json_item(json_item, schema)
        if err is not None:
            emitter.publish(err)
            return 1

        key, value = key_value
        if key in app_json:
            emitter.publish(
                'Key {!r} was specified more than once'.format(key))
            return 1
        else:
            app_json[key] = value

    err = util.validate_json(app_json, schema)
    if err is not None:
        emitter.publish(err)
        return 1

    deployment, err = client.update_app(app_id, app_json, force)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish('Created deployment {}'.format(deployment))

    return 0


def _restart(app_id, force):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param force: whether to override running deployments
    :type force: bool
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    desc, err = client.get_app(app_id)
    if err is not None:
        emitter.publish(err)
        return 1

    if desc['instances'] <= 0:
        app_id = marathon.normalize_app_id(app_id)
        emitter.publish(
            'Unable to restart application {!r} because it is stopped'.format(
                app_id,
                desc['instances']))
        return 1

    payload, err = client.restart_app(app_id, force)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish('Created deployment {}'.format(payload['deploymentId']))

    return 0


def _version_list(app_id, max_count):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param max_count: the maximum number of version to fetch and return
    :type max_count: str
    :returns: process status
    :rtype: int
    """

    if max_count is not None:
        max_count, err = _parse_int(max_count)
        if err is not None:
            emitter.publish(err)
            return 1

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    versions, err = client.get_app_versions(app_id, max_count)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish(versions)

    return 0


def _deployment_list(app_id):
    """
    :param app_id: the application id
    :type app_id: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    deployments, err = client.get_deployments(app_id)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish(deployments)

    return 0


def _deployment_stop(deployment_id):
    """
    :param deployment_id: the application id
    :type deployment_di: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    err = client.stop_deployment(deployment_id)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _deployment_rollback(deployment_id):
    """
    :param deployment_id: the application id
    :type deployment_di: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    err = client.rollback_deployment(deployment_id)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _deployment_watch(deployment_id, max_count, interval):
    """
    :param deployment_id: the application id
    :type deployment_di: str
    :param max_count: maximum number of polling calls
    :type max_count: str
    :param interval: wait interval in seconds between polling calls
    :type interval: str
    :returns: process status
    :rtype: int
    """

    if max_count is not None:
        max_count, err = _parse_int(max_count)
        if err is not None:
            emitter.publish(err)
            return 1

    if interval is not None:
        interval, err = _parse_int(interval)
        if err is not None:
            emitter.publish(err)
            return 1
    else:
        interval = 1

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    count = 0
    while max_count is None or count < max_count:
        deployment, err = client.get_deployment(deployment_id)
        if err is not None:
            emitter.publish(err)
            return 1

        if deployment is None:
            return 0

        emitter.publish(deployment)
        time.sleep(interval)
        count += 1

    return 0


def _update_from_stdin(app_id, force):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param force: whether to override running deployments
    :type force: bool
    :returns: process status
    :rtype: int
    """

    logger.info('Updating %r from JSON object from stdin', app_id)

    application_resource, err = util.load_jsons(sys.stdin.read())
    if err is not None:
        emitter.publish(err)
        return 1

    # Add application to marathon
    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    _, err = client.update_app(app_id, application_resource, force)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _calculate_version(client, app_id, version):
    """
    :param client: Marathon client
    :type client: dcos.api.marathon.Client
    :param app_id: The ID of the application
    :type app_id: str
    :param version: Relative or absolute version or None
    :type version: str
    :returns: The absolute version as an ISO8601 date-time; Error otherwise
    :rtype: (str, Error)
    """

    # First let's try to parse it as a negative integer
    value, err = _parse_int(version)
    if err is None and value < 0:
        value = -1 * value
        # We have a negative value let's ask Marathon for the last abs(value)
        versions, err = client.get_app_versions(app_id, value + 1)
        if err is not None:
            return (None, err)

        if len(versions) <= value:
            # We don't have enough versions. Return an error.
            msg = "Application {!r} only has {!r} version(s)."
            return (
                None,
                errors.DefaultError(msg.format(app_id, len(versions), value))
            )
        else:
            return (versions[value], None)
    elif err is None:
        return (
            None,
            errors.DefaultError(
                'Relative versions must be negative: {}'.format(version))
        )
    else:
        # Let's assume that we have an absolute version
        return (version, None)


def _parse_int(string):
    """
    :param string: String to parse as an integer
    :type string: str
    :returns: The interger value of the string
    :rtype: (int, Error)
    """

    try:
        return (int(string), None)
    except:
        error = sys.exc_info()[0]
        logger = util.get_logger(__name__)
        logger.error(
            'Unhandled exception while parsing string as int: %r -- %r',
            string,
            error)
        return (None, errors.DefaultError('Error parsing string as int'))
