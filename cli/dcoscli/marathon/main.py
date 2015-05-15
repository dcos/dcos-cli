"""Deploy and manage applications on the DCOS

Usage:
    dcos marathon --config-schema
    dcos marathon --info
    dcos marathon about
    dcos marathon app add [<app-resource>]
    dcos marathon app list
    dcos marathon app remove [--force] <app-id>
    dcos marathon app restart [--force] <app-id>
    dcos marathon app show [--app-version=<app-version>] <app-id>
    dcos marathon app start [--force] <app-id> [<instances>]
    dcos marathon app stop [--force] <app-id>
    dcos marathon app update [--force] <app-id> [<properties>...]
    dcos marathon app version list [--max-count=<max-count>] <app-id>
    dcos marathon deployment list [<app-id>]
    dcos marathon deployment rollback <deployment-id>
    dcos marathon deployment stop <deployment-id>
    dcos marathon deployment watch [--max-count=<max-count>]
         [--interval=<interval>] <deployment-id>
    dcos marathon task list [<app-id>]
    dcos marathon task show <task-id>

Options:
    -h, --help                   Show this screen
    --info                       Show a short description of this subcommand
    --version                    Show version
    --force                      This flag disable checks in Marathon during
                                 update operations
    --app-version=<app-version>  This flag specifies the application version to
                                 use for the command. The application version
                                 (<app-version>) can be specified as an
                                 absolute value or as relative value. Absolute
                                 version values must be in ISO8601 date format.
                                 Relative values must be specified as a
                                 negative integer and they represent the
                                 version from the currently deployed
                                 application definition
    --config-schema              Show the configuration schema for the Marathon
                                 subcommand
    --max-count=<max-count>      Maximum number of entries to try to fetch and
                                 return
    --interval=<interval>        Number of seconds to wait between actions

Positional arguments:
    <app-id>                    The application id
    <app-resource>              The application resource; for a detailed
                                description see (https://mesosphere.github.io/
                                marathon/docs/rest-api.html#post-/v2/apps)
    <deployment-id>             The deployment id
    <instances>                 The number of instances to start
    <properties>                Optional key-value pairs to be included in the
                                command. The separator between the key and
                                value must be the '=' character. E.g. cpus=2.0
    <task-id>                   The task id
"""
import json
import sys
import time

import dcoscli
import docopt
import pkg_resources
from dcos import cmds, emitting, jsonitem, marathon, options, util
from dcos.errors import DCOSException

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _main():
    util.configure_logger_from_environ()

    args = docopt.docopt(
        __doc__,
        version='dcos-marathon version {}'.format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: all the supported commands
    :rtype: dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['marathon', 'version', 'list'],
            arg_keys=['<app-id>', '--max-count'],
            function=_version_list),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'list'],
            arg_keys=['<app-id>'],
            function=_deployment_list),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'rollback'],
            arg_keys=['<deployment-id>'],
            function=_deployment_rollback),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'stop'],
            arg_keys=['<deployment-id>'],
            function=_deployment_stop),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'watch'],
            arg_keys=['<deployment-id>', '--max-count', '--interval'],
            function=_deployment_watch),

        cmds.Command(
            hierarchy=['marathon', 'task', 'list'],
            arg_keys=['<app-id>'],
            function=_task_list),

        cmds.Command(
            hierarchy=['marathon', 'task', 'show'],
            arg_keys=['<task-id>'],
            function=_task_show),

        cmds.Command(
            hierarchy=['marathon', 'app', 'add'],
            arg_keys=['<app-resource>'],
            function=_add),

        cmds.Command(
            hierarchy=['marathon', 'app', 'list'],
            arg_keys=[],
            function=_list),

        cmds.Command(
            hierarchy=['marathon', 'app', 'remove'],
            arg_keys=['<app-id>', '--force'],
            function=_remove),

        cmds.Command(
            hierarchy=['marathon', 'app', 'show'],
            arg_keys=['<app-id>', '--app-version'],
            function=_show),

        cmds.Command(
            hierarchy=['marathon', 'app', 'start'],
            arg_keys=['<app-id>', '<instances>', '--force'],
            function=_start),

        cmds.Command(
            hierarchy=['marathon', 'app', 'stop'],
            arg_keys=['<app-id>', '--force'],
            function=_stop),

        cmds.Command(
            hierarchy=['marathon', 'app', 'update'],
            arg_keys=['<app-id>', '<properties>', '--force'],
            function=_update),

        cmds.Command(
            hierarchy=['marathon', 'app', 'restart'],
            arg_keys=['<app-id>', '--force'],
            function=_restart),

        cmds.Command(
            hierarchy=['marathon', 'about'],
            arg_keys=[],
            function=_about),

        cmds.Command(
            hierarchy=['marathon'],
            arg_keys=['--config-schema', '--info'],
            function=_marathon)
    ]


def _marathon(config_schema, info):
    """
    :param config_schema: Whether to output the config schema
    :type config_schema: boolean
    :param info: Whether to output a description of this subcommand
    :type info: boolean
    :returns: Process status
    :rtype: int
    """

    if config_schema:
        schema = json.loads(
            pkg_resources.resource_string(
                'dcoscli',
                'data/config-schema/marathon.json').decode('utf-8'))
        emitter.publish(schema)
    elif info:
        _info()
    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return 0


def _info():
    """
    :returns: Process status
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _about():
    """
    :returns: Process status
    :rtype: int
    """

    client = marathon.create_client()

    emitter.publish(client.get_about())
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
            application_resource = util.load_json(fd)
    else:
        # Check that stdin is not tty
        if sys.stdin.isatty():
            # We don't support TTY right now. In the future we will start an
            # editor
            raise DCOSException(
                "We currently don't support reading from the TTY. Please "
                "specify an application JSON.\n"
                "Usage: dcos app add < app_resource.json")

        application_resource = util.load_json(sys.stdin)

    schema = json.loads(
        pkg_resources.resource_string(
            'dcoscli',
            'data/marathon-schema.json').decode('utf-8'))

    errs = util.validate_json(application_resource, schema)
    if errs:
        raise DCOSException(util.list_to_err(errs))

    # Add application to marathon
    client = marathon.create_client()

    # Check that the application doesn't exist
    app_id = client.normalize_app_id(application_resource['id'])

    try:
        client.get_app(app_id)
    except DCOSException as e:
        logger.exception(e)
    else:
        raise DCOSException("Application '{}' already exists".format(app_id))

    client.add_app(application_resource)

    return 0


def _list():
    """
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client()
    apps = client.get_apps()

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

    client = marathon.create_client()
    client.remove_app(app_id, force)
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

    client = marathon.create_client()

    if version is not None:
        version = _calculate_version(client, app_id, version)

    app = client.get_app(app_id, version=version)

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
    client = marathon.create_client()

    desc = client.get_app(app_id)

    if desc['instances'] > 0:
        emitter.publish(
            'Application {!r} already started: {!r} instances.'.format(
                app_id,
                desc['instances']))
        return 1

    schema = json.loads(
        pkg_resources.resource_string(
            'dcoscli',
            'data/marathon-schema.json').decode('utf-8'))

    # Need to add the 'id' because it is required
    app_json = {'id': app_id}

    # Set instances to 1 if not specified
    if instances is None:
        instances = 1
    else:
        instances = util.parse_int(instances)
        if instances <= 0:
            emitter.publish(
                'The number of instances must be positive: {!r}.'.format(
                    instances))
            return 1

    app_json['instances'] = instances

    errs = util.validate_json(app_json, schema)
    if errs:
        raise DCOSException(util.list_to_err(errs))

    deployment = client.update_app(app_id, app_json, force)

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
    client = marathon.create_client()

    desc = client.get_app(app_id)

    if desc['instances'] <= 0:
        emitter.publish(
            'Application {!r} already stopped: {!r} instances.'.format(
                app_id,
                desc['instances']))
        return 1

    app_json = {'instances': 0}

    deployment = client.update_app(app_id, app_json, force)

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

    client = marathon.create_client()

    # Ensure that the application exists
    client.get_app(app_id)

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
            'dcoscli',
            'data/marathon-schema.json').decode('utf-8'))

    # Need to add the 'id' because it is required
    app_json = {'id': app_id}

    for json_item in json_items:
        key, value = jsonitem.parse_json_item(json_item, schema)

        if key in app_json:
            emitter.publish(
                'Key {!r} was specified more than once'.format(key))
            return 1
        else:
            app_json[key] = value

    errs = util.validate_json(app_json, schema)
    if errs:
        raise DCOSException(util.list_to_err(errs))

    deployment = client.update_app(app_id, app_json, force)

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

    client = marathon.create_client()

    desc = client.get_app(app_id)

    if desc['instances'] <= 0:
        app_id = client.normalize_app_id(app_id)
        emitter.publish(
            'Unable to perform rolling restart of application {!r} '
            'because it has no running tasks'.format(
                app_id,
                desc['instances']))
        return 1

    payload = client.restart_app(app_id, force)

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
        max_count = util.parse_int(max_count)

    client = marathon.create_client()

    versions = client.get_app_versions(app_id, max_count)

    emitter.publish(versions)
    return 0


def _deployment_list(app_id):
    """
    :param app_id: the application id
    :type app_id: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client()

    deployments = client.get_deployments(app_id)

    emitter.publish(deployments)
    return 0


def _deployment_stop(deployment_id):
    """
    :param deployment_id: the application id
    :type deployment_di: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client()
    client.stop_deployment(deployment_id)

    return 0


def _deployment_rollback(deployment_id):
    """
    :param deployment_id: the application id
    :type deployment_di: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client()
    deployment = client.rollback_deployment(deployment_id)

    emitter.publish(deployment)
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
        max_count = util.parse_int(max_count)

    interval = 1 if interval is None else util.parse_int(interval)

    client = marathon.create_client()

    count = 0
    while max_count is None or count < max_count:
        deployment = client.get_deployment(deployment_id)

        if deployment is None:
            return 0

        emitter.publish(deployment)
        time.sleep(interval)
        count += 1

    return 0


def _task_list(app_id):
    """
    :param app_id: the id of the application
    :type app_id: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client()
    tasks = client.get_tasks(app_id)

    emitter.publish(tasks)
    return 0


def _task_show(task_id):
    """
    :param task_id: the task id
    :type task_id: str
    :returns: process status
    :rtype: int
    """

    client = marathon.create_client()
    task = client.get_task(task_id)

    if task is None:
        raise DCOSException("Task '{}' does not exist".format(task_id))

    emitter.publish(task)
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

    application_resource = util.load_jsons(sys.stdin.read())

    # Add application to marathon
    client = marathon.create_client()

    client.update_app(app_id, application_resource, force)

    return 0


def _calculate_version(client, app_id, version):
    """
    :param client: Marathon client
    :type client: dcos.marathon.Client
    :param app_id: The ID of the application
    :type app_id: str
    :param version: Relative or absolute version or None
    :type version: str
    :returns: The absolute version as an ISO8601 date-time
    :rtype: str
    """

    # First let's try to parse it as a negative integer
    try:
        value = util.parse_int(version)
    except DCOSException:
        return version
    else:
        if value < 0:
            value = -1 * value
            # We have a negative value let's ask Marathon for the last
            # abs(value)
            versions = client.get_app_versions(app_id, value + 1)

            if len(versions) <= value:
                # We don't have enough versions. Return an error.
                msg = "Application {!r} only has {!r} version(s)."
                raise DCOSException(msg.format(app_id, len(versions), value))
            else:
                return versions[value]
        else:
            raise DCOSException(
                'Relative versions must be negative: {}'.format(version))
