"""Deploy and manage applications on the DCOS

Usage:
    dcos marathon --config-schema
    dcos marathon --info
    dcos marathon about
    dcos marathon app add [<app-resource>]
    dcos marathon app list [--json]
    dcos marathon app remove [--force] <app-id>
    dcos marathon app restart [--force] <app-id>
    dcos marathon app show [--app-version=<app-version>] <app-id>
    dcos marathon app start [--force] <app-id> [<instances>]
    dcos marathon app stop [--force] <app-id>
    dcos marathon app update [--force] <app-id> [<properties>...]
    dcos marathon app scale [--force] <app-id> <instances>
    dcos marathon app version list [--max-count=<max-count>] <app-id>
    dcos marathon deployment list [--json <app-id>]
    dcos marathon deployment rollback <deployment-id>
    dcos marathon deployment stop <deployment-id>
    dcos marathon deployment watch [--max-count=<max-count>]
         [--interval=<interval>] <deployment-id>
    dcos marathon task list [--json <app-id>]
    dcos marathon task show <task-id>
    dcos marathon group add [<group-resource>]
    dcos marathon group list [--json]
    dcos marathon group show [--group-version=<group-version>] <group-id>
    dcos marathon group remove [--force] <group-id>
    dcos marathon group update [--force] <group-id> [<properties>...]
    dcos marathon group scale [--force] <group-id> <scale-factor>

Options:
    -h, --help                       Show this screen

    --info                           Show a short description of this
                                     subcommand

     --json                          Print json-formatted tasks

    --version                        Show version

    --force                          This flag disable checks in Marathon
                                     during update operations

    --app-version=<app-version>      This flag specifies the application
                                     version to use for the command. The
                                     application version (<app-version>) can be
                                     specified as an absolute value or as
                                     relative value. Absolute version values
                                     must be in ISO8601 date format. Relative
                                     values must be specified as a negative
                                     integer and they represent the version
                                     from the currently deployed application
                                     definition

    --group-version=<group-version>  This flag specifies the group version to
                                     use for the command. The group version
                                     (<group-version>) can be specified as an
                                     absolute value or as relative value.
                                     Absolute version values must be in ISO8601
                                     date format. Relative values must be
                                     specified as a negative integer and they
                                     represent the version from the currently
                                     deployed group definition

    --config-schema                  Show the configuration schema for the
                                     Marathon subcommand

    --max-count=<max-count>          Maximum number of entries to try to fetch
                                     and return

    --interval=<interval>            Number of seconds to wait between actions

Positional Arguments:
    <app-id>                    The application id

    <app-resource>              Path to a file containing the app's JSON
                                definition. If omitted, the definition is read
                                from stdin. For a detailed description see
                                (https://mesosphere.github.io/
                                marathon/docs/rest-api.html#post-/v2/apps).

    <deployment-id>             The deployment id

    <group-id>                  The group id

    <group-resource>            Path to a file containing the group's JSON
                                definition. If omitted, the definition is read
                                from stdin. For a detailed description see
                                (https://mesosphere.github.io/
                                marathon/docs/rest-api.html#post-/v2/groups).

    <instances>                 The number of instances to start

    <properties>                Must be of the format <key>=<value>. E.g.
                                cpus=2.0. If omitted, properties are read from
                                stdin.

    <task-id>                   The task id

    <scale-factor>              The value of scale-factor for a group
"""
import json
import sys
import time

import dcoscli
import docopt
import pkg_resources
from dcos import cmds, emitting, jsonitem, marathon, options, util
from dcos.errors import DCOSException
from dcoscli import tables

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
            arg_keys=['<app-id>', '--json'],
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
            arg_keys=['<app-id>', '--json'],
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
            arg_keys=['--json'],
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
            hierarchy=['marathon', 'app', 'scale'],
            arg_keys=['<app-id>', '<instances>', '--force'],
            function=_scale),

        cmds.Command(
            hierarchy=['marathon', 'app', 'restart'],
            arg_keys=['<app-id>', '--force'],
            function=_restart),

        cmds.Command(
            hierarchy=['marathon', 'group', 'add'],
            arg_keys=['<group-resource>'],
            function=_group_add),

        cmds.Command(
            hierarchy=['marathon', 'group', 'list'],
            arg_keys=['--json'],
            function=_group_list),

        cmds.Command(
            hierarchy=['marathon', 'group', 'show'],
            arg_keys=['<group-id>', '--group-version'],
            function=_group_show),

        cmds.Command(
            hierarchy=['marathon', 'group', 'remove'],
            arg_keys=['<group-id>', '--force'],
            function=_group_remove),

        cmds.Command(
            hierarchy=['marathon', 'group', 'update'],
            arg_keys=['<group-id>', '<properties>', '--force'],
            function=_group_update),

        cmds.Command(
            hierarchy=['marathon', 'group', 'scale'],
            arg_keys=['<group-id>', '<scale-factor>', '--force'],
            function=_group_scale),

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
    :returns: process return code
    :rtype: int
    """

    if config_schema:
        schema = _cli_config_schema()
        emitter.publish(schema)
    elif info:
        _info()
    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return 0


def _info():
    """
    :returns: process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _about():
    """
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    emitter.publish(client.get_about())
    return 0


def _get_resource(resource):
    """
    :param resource: optional filename for the application or group resource
    :type resource: str
    :returns: resource
    :rtype: dict
    """
    if resource is not None:
        with util.open_file(resource) as resource_file:
            return util.load_json(resource_file)

    # Check that stdin is not tty
    if sys.stdin.isatty():
        # We don't support TTY right now. In the future we will start an
        # editor
        raise DCOSException(
            "We currently don't support reading from the TTY. Please "
            "specify an application JSON.\n"
            "Usage: dcos app add < app_resource.json")

    return util.load_json(sys.stdin)


def _add(app_resource):
    """
    :param app_resource: optional filename for the application resource
    :type app_resource: str
    :returns: process return code
    :rtype: int
    """
    application_resource = _get_resource(app_resource)

    # Add application to marathon
    client = marathon.create_client()

    schema = client.get_app_schema()
    if schema is None:
        schema = _app_schema()

    errs = util.validate_json(application_resource, schema)
    if errs:
        raise DCOSException(util.list_to_err(errs))

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


def _list(json_):
    """
    :param json_: output json if True
    :type json_: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()
    apps = client.get_apps()

    if json_:
        emitter.publish(apps)
    else:
        deployments = client.get_deployments()
        table = tables.app_table(apps, deployments)
        output = str(table)
        if output:
            emitter.publish(output)

    return 0


def _group_list(json_):
    """
    :param json_: output json if True
    :type json_: bool
    :rtype: int
    :returns: process return code
    """

    client = marathon.create_client()
    groups = client.get_groups()

    emitting.publish_table(emitter, groups, tables.group_table, json_)
    return 0


def _group_add(group_resource):
    """
    :param group_resource: optional filename for the group resource
    :type group_resource: str
    :returns: process return code
    :rtype: int
    """

    group_resource = _get_resource(group_resource)
    schema = _data_schema()

    errs = util.validate_json(group_resource, schema)
    if errs:
        raise DCOSException(util.list_to_err(errs))

    client = marathon.create_client()

    # Check that the group doesn't exist
    group_id = client.normalize_app_id(group_resource['id'])

    try:
        client.get_group(group_id)
    except DCOSException as e:
        logger.exception(e)
    else:
        raise DCOSException("Group '{}' already exists".format(group_id))

    client.create_group(group_resource)

    return 0


def _remove(app_id, force):
    """
    :param app_id: ID of the app to remove
    :type app_id: str
    :param force: Whether to override running deployments.
    :type force: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()
    client.remove_app(app_id, force)
    return 0


def _group_remove(group_id, force):
    """
    :param group_id: ID of the app to remove
    :type group_id: str
    :param force: Whether to override running deployments.
    :type force: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()
    client.remove_group(group_id, force)
    return 0


def _show(app_id, version):
    """Show details of a Marathon application.

    :param app_id: The id for the application
    :type app_id: str
    :param version: The version, either absolute (date-time) or relative
    :type version: str
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    if version is not None:
        version = _calculate_version(client, app_id, version)

    app = client.get_app(app_id, version=version)

    emitter.publish(app)
    return 0


def _group_show(group_id, version=None):
    """Show details of a Marathon application.

    :param group_id: The id for the application
    :type group_id: str
    :param version: The version, either absolute (date-time) or relative
    :type version: str
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    app = client.get_group(group_id, version=version)

    emitter.publish(app)
    return 0


def _group_update(group_id, properties, force):
    """
    :param group_id: the id of the group
    :type group_id: str
    :param properties: json items used to update group
    :type properties: [str]
    :param force: whether to override running deployments
    :type force: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    # Ensure that the group exists
    current_group = client.get_group(group_id)

    schema = _data_schema()
    group_resource = _parse_properties(properties, schema)
    _validate_update(current_group, group_resource, schema)

    deployment = client.update_group(group_id, group_resource, force)

    emitter.publish('Created deployment {}'.format(deployment))
    return 0


def _start(app_id, instances, force):
    """Start a Marathon application.

    :param app_id: the id for the application
    :type app_id: str
    :param instances: the number of instances to start
    :type instances: str
    :param force: whether to override running deployments
    :type force: bool
    :returns: process return code
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

    deployment = client.update_app(app_id, app_json, force)

    emitter.publish('Created deployment {}'.format(deployment))

    return 0


def _stop(app_id, force):
    """Stop a Marathon application

    :param app_id: the id of the application
    :type app_id: str
    :param force: whether to override running deployments
    :type force: bool
    :returns: process return code
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


def _update(app_id, properties, force):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param properties: json items used to update resource
    :type properties: [str]
    :param force: whether to override running deployments
    :type force: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    # Ensure that the application exists
    current_app = client.get_app(app_id)

    schema = _app_schema()
    app_resource = _parse_properties(properties, schema)
    _validate_update(current_app, app_resource, schema)

    deployment = client.update_app(app_id, app_resource, force)

    emitter.publish('Created deployment {}'.format(deployment))
    return 0


def _scale(app_id, instances, force):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param instances: amount of new instances
    :type force: int
    :param force: whether to override running deployments
    :type force: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    deployment = client.scale_app(app_id, instances, force)
    emitter.publish('Created deployment {}'.format(deployment))
    return 0


def _group_scale(group_id, scale_factor, force):
    """
    :param group_id: the id of the group
    :type group_id: str
    :param scale_factor: scale factor for group instances
    :type properties: float
    :param force: whether to override running deployments
    :type force: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    deployment = client.scale_group(group_id, scale_factor, force)
    emitter.publish('Created deployment {}'.format(deployment))
    return 0


def _validate_update(current_resource, properties, schema):
    """
    Validate resource ("app" or "group") update

    :param current_resource: Marathon app definition
    :type current_resource: dict
    :param properties: resource JSON
    :type properties: dict
    :param schema: JSON schema used to verify properties
    :type schema: dict
    :rtype: None
    """
    updated_resource = _clean_up_resource_definition(current_resource.copy())
    updated_resource.update(properties)

    errs = util.validate_json(updated_resource, schema)
    if errs:
        raise DCOSException(util.list_to_err(errs))


def _clean_up_resource_definition(properties):
    """
    Remove task properties and nulls from resource definition

    :param properties: resource JSON
    :type properties: dict
    :returns: resource JSON
    :rtype: dict
    """
    clean_properties = {}
    for k, v in properties.items():
        if v:
            if k in ["apps", "groups"]:
                clean_properties[k] = [_clean_up_resource_definition(v[0])]
            elif not k.startswith("task"):
                clean_properties[k] = v

    return clean_properties


def _parse_properties(properties, schema):
    """
    :param properties: JSON items in the form key=value
    :type properties: [str]
    :param schema: The JSON schema used to verify properties
    :type schema: dict
    :returns: resource JSON
    :rtype: dict
    """

    if len(properties) == 0:
        if sys.stdin.isatty():
            # We don't support TTY right now. In the future we will start an
            # editor
            raise DCOSException(
                "We currently don't support reading from the TTY. Please "
                "specify an application JSON.\n"
                "E.g. dcos marathon app update < app_update.json")
        else:
            return util.load_jsons(sys.stdin.read())

    resource_json = {}
    for prop in properties:
        key, value = jsonitem.parse_json_item(prop, schema)

        key = jsonitem.clean_value(key)
        if key in resource_json:
            raise DCOSException(
                'Key {!r} was specified more than once'.format(key))

        resource_json[key] = value

    return resource_json


def _restart(app_id, force):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param force: whether to override running deployments
    :type force: bool
    :returns: process return code
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
    :returns: process return code
    :rtype: int
    """

    if max_count is not None:
        max_count = util.parse_int(max_count)

    client = marathon.create_client()

    versions = client.get_app_versions(app_id, max_count)

    emitter.publish(versions)
    return 0


def _deployment_list(app_id, json_):
    """
    :param app_id: the application id
    :type app_id: str
    :param json_: output json if True
    :type json_: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()

    deployments = client.get_deployments(app_id)

    emitting.publish_table(emitter,
                           deployments,
                           tables.deployment_table,
                           json_)
    return 0


def _deployment_stop(deployment_id):
    """
    :param deployment_id: the application id
    :type deployment_di: str
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()
    client.stop_deployment(deployment_id)

    return 0


def _deployment_rollback(deployment_id):
    """
    :param deployment_id: the application id
    :type deployment_di: str
    :returns: process return code
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
    :returns: process return code
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


def _task_list(app_id, json_):
    """
    :param app_id: the id of the application
    :type app_id: str
    :param json_: output json if True
    :type json_: bool
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()
    tasks = client.get_tasks(app_id)

    emitting.publish_table(emitter, tasks, tables.app_task_table, json_)
    return 0


def _task_show(task_id):
    """
    :param task_id: the task id
    :type task_id: str
    :returns: process return code
    :rtype: int
    """

    client = marathon.create_client()
    task = client.get_task(task_id)

    if task is None:
        raise DCOSException("Task '{}' does not exist".format(task_id))

    emitter.publish(task)
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


def _cli_config_schema():
    """
    :returns: schema for marathon cli config
    :rtype: dict
    """
    return json.loads(
        pkg_resources.resource_string(
            'dcoscli',
            'data/config-schema/marathon.json').decode('utf-8'))


def _data_schema():
    """
    :returns: schema for marathon data
    :rtype: dict
    """
    return json.loads(
        pkg_resources.resource_string(
            'dcoscli',
            'data/marathon-group-schema.json').decode('utf-8'))


def _app_schema():
    """
    :returns: schema for apps
    :rtype: dict
    """
    return _data_schema()['definitions']['app']
