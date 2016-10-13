import json
import os
import sys
import time

import docopt
import pkg_resources
import six

import dcoscli
from dcos import cmds, emitting, http, jsonitem, marathon, options, util
from dcos.errors import DCOSException
from dcoscli import tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("marathon"),
        argv=argv,
        version='dcos-marathon version {}'.format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: all the supported commands
    :rtype: dcos.cmds.Command
    """

    subcommand = MarathonSubcommand()

    return [
        cmds.Command(
            hierarchy=['marathon', 'version', 'list'],
            arg_keys=['<app-id>', '--max-count'],
            function=subcommand.version_list),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'list'],
            arg_keys=['<app-id>', '--json'],
            function=subcommand.deployment_list),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'rollback'],
            arg_keys=['<deployment-id>'],
            function=subcommand.deployment_rollback),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'stop'],
            arg_keys=['<deployment-id>'],
            function=subcommand.deployment_stop),

        cmds.Command(
            hierarchy=['marathon', 'deployment', 'watch'],
            arg_keys=['<deployment-id>', '--max-count', '--interval'],
            function=subcommand.deployment_watch),

        cmds.Command(
            hierarchy=['marathon', 'task', 'list'],
            arg_keys=['<app-id>', '--json'],
            function=subcommand.task_list),

        cmds.Command(
            hierarchy=['marathon', 'task', 'stop'],
            arg_keys=['<task-id>', '--wipe'],
            function=subcommand.task_stop),

        cmds.Command(
            hierarchy=['marathon', 'task', 'show'],
            arg_keys=['<task-id>'],
            function=subcommand.task_show),

        cmds.Command(
            hierarchy=['marathon', 'app', 'add'],
            arg_keys=['<app-resource>'],
            function=subcommand.add),

        cmds.Command(
            hierarchy=['marathon', 'app', 'list'],
            arg_keys=['--json'],
            function=subcommand.list),

        cmds.Command(
            hierarchy=['marathon', 'app', 'remove'],
            arg_keys=['<app-id>', '--force'],
            function=subcommand.remove),

        cmds.Command(
            hierarchy=['marathon', 'app', 'show'],
            arg_keys=['<app-id>', '--app-version'],
            function=subcommand.show),

        cmds.Command(
            hierarchy=['marathon', 'app', 'start'],
            arg_keys=['<app-id>', '<instances>', '--force'],
            function=subcommand.start),

        cmds.Command(
            hierarchy=['marathon', 'app', 'stop'],
            arg_keys=['<app-id>', '--force'],
            function=subcommand.stop),

        cmds.Command(
            hierarchy=['marathon', 'app', 'update'],
            arg_keys=['<app-id>', '<properties>', '--force'],
            function=subcommand.update),

        cmds.Command(
            hierarchy=['marathon', 'app', 'restart'],
            arg_keys=['<app-id>', '--force'],
            function=subcommand.restart),

        cmds.Command(
            hierarchy=['marathon', 'app', 'kill'],
            arg_keys=['<app-id>', '--scale', '--host'],
            function=subcommand.kill),

        cmds.Command(
            hierarchy=['marathon', 'group', 'add'],
            arg_keys=['<group-resource>'],
            function=subcommand.group_add),

        cmds.Command(
            hierarchy=['marathon', 'group', 'list'],
            arg_keys=['--json'],
            function=subcommand.group_list),

        cmds.Command(
            hierarchy=['marathon', 'group', 'show'],
            arg_keys=['<group-id>', '--group-version'],
            function=subcommand.group_show),

        cmds.Command(
            hierarchy=['marathon', 'group', 'remove'],
            arg_keys=['<group-id>', '--force'],
            function=subcommand.group_remove),

        cmds.Command(
            hierarchy=['marathon', 'group', 'update'],
            arg_keys=['<group-id>', '<properties>', '--force'],
            function=subcommand.group_update),

        cmds.Command(
            hierarchy=['marathon', 'group', 'scale'],
            arg_keys=['<group-id>', '<scale-factor>', '--force'],
            function=subcommand.group_scale),

        cmds.Command(
            hierarchy=['marathon', 'pod', 'add'],
            arg_keys=['<pod-resource>'],
            function=subcommand.pod_add),

        cmds.Command(
            hierarchy=['marathon', 'pod', 'remove'],
            arg_keys=['<pod-id>', '--force'],
            function=subcommand.pod_remove),

        cmds.Command(
            hierarchy=['marathon', 'pod', 'list'],
            arg_keys=['--json'],
            function=subcommand.pod_list),

        cmds.Command(
            hierarchy=['marathon', 'pod', 'show'],
            arg_keys=['<pod-id>'],
            function=subcommand.pod_show),

        cmds.Command(
            hierarchy=['marathon', 'pod', 'update'],
            arg_keys=['<pod-id>', '--force'],
            function=subcommand.pod_update),

        cmds.Command(
            hierarchy=['marathon', 'pod', 'kill'],
            arg_keys=['<pod-id>', '<instance-ids>'],
            function=subcommand.pod_kill),

        cmds.Command(
            hierarchy=['marathon', 'about'],
            arg_keys=[],
            function=subcommand.about),

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
        doc = default_command_info("marathon")
        emitter.publish(options.make_generic_usage_message(doc))
        return 1

    return 0


def _info():
    """
    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("marathon"))
    return 0


class ResourceReader(object):
    """Encapsulates side-effecting methods for loading Marathon resources."""

    @staticmethod
    def get_resource(name):
        """
        :param name: optional filename or http(s) url
        for the application or group resource
        :type name: str | None
        :returns: resource
        :rtype: dict
        """
        if name is not None:
            if os.path.isfile(name):
                with util.open_file(name) as resource_file:
                    return util.load_json(resource_file)
            else:
                try:
                    http.silence_requests_warnings()
                    req = http.get(name)
                    if req.status_code == 200:
                        data = b''
                        for chunk in req.iter_content(1024):
                            data += chunk
                        return util.load_jsons(data.decode('utf-8'))
                    else:
                        raise Exception
                except Exception:
                    logger.exception('Cannot read from resource %s', name)
                    raise DCOSException(
                        "Can't read from resource: {0}.\n"
                        "Please check that it exists.".format(name))

        example = "E.g.: dcos marathon app add < app_resource.json"
        ResourceReader._assert_no_tty(example)

        return util.load_json(sys.stdin)

    @staticmethod
    def get_resource_from_properties(properties):
        """
        :param properties: JSON items in the form key=value
        :type properties: [str]
        :returns: resource JSON
        :rtype: dict
        """

        if len(properties) == 0:
            example =\
                "E.g. dcos marathon app update your-app-id < app_update.json"
            ResourceReader._assert_no_tty(example)

            return util.load_jsons(sys.stdin.read())

        resource_json = {}
        for prop in properties:
            key, value = jsonitem.parse_json_item(prop, None)

            key = jsonitem.clean_value(key)
            if key in resource_json:
                raise DCOSException(
                    'Key {!r} was specified more than once'.format(key))

            resource_json[key] = value
        return resource_json

    @staticmethod
    def _assert_no_tty(command_example):
        if sys.stdin.isatty():
            # We don't support TTY right now.
            # In the future we will start an editor
            template = ("We currently don't support reading from the TTY. "
                        "Please specify an application JSON.\n{}")
            raise DCOSException(template.format(command_example))


class MarathonSubcommand(object):
    """Defines a method for each operation of the `dcos marathon` subcommand.

    :param resource_reader: provides input methods for Marathon resources
    :type resource_reader: ResourceReader
    :param create_marathon_client: a callable that returns an instance of
                                   marathon.Client
    :type create_marathon_client: collections.abc.Callable
    """

    def __init__(self,
                 resource_reader=ResourceReader(),
                 create_marathon_client=marathon.create_client):
        self._resource_reader = resource_reader
        self._create_marathon_client = create_marathon_client

    def about(self):
        """
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()

        emitter.publish(client.get_about())
        return 0

    def add(self, app_resource):
        """
        :param app_resource: optional filename for the application resource
        :type app_resource: str
        :returns: process return code
        :rtype: int
        """
        application_resource = self._resource_reader.get_resource(app_resource)

        # Add application to marathon
        client = self._create_marathon_client()

        # Check that the application doesn't exist
        app_id = util.normalize_marathon_id_path(application_resource['id'])

        try:
            client.get_app(app_id)
        except DCOSException as e:
            logger.exception(e)
        else:
            message = "Application '{}' already exists".format(app_id)
            raise DCOSException(message)

        deployment = client.add_app(application_resource)
        emitter.publish('Created deployment {}'.format(deployment))

        return 0

    def list(self, json_):
        """
        :param json_: output json if True
        :type json_: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        apps = client.get_apps()

        if json_:
            emitter.publish(apps)
        else:
            deployments = client.get_deployments()
            table = tables.app_table(apps, deployments)
            output = six.text_type(table)
            if output:
                emitter.publish(output)

        return 0

    def group_list(self, json_):
        """
        :param json_: output json if True
        :type json_: bool
        :rtype: int
        :returns: process return code
        """

        client = self._create_marathon_client()
        groups = client.get_groups()

        emitting.publish_table(emitter, groups, tables.group_table, json_)
        return 0

    def group_add(self, group_resource):
        """
        :param group_resource: optional filename for the group resource
        :type group_resource: str
        :returns: process return code
        :rtype: int
        """

        group_resource = self._resource_reader.get_resource(group_resource)

        client = self._create_marathon_client()

        # Check that the group doesn't exist
        group_id = util.normalize_marathon_id_path(group_resource['id'])

        try:
            client.get_group(group_id)
        except DCOSException as e:
            logger.exception(e)
        else:
            raise DCOSException("Group '{}' already exists".format(group_id))

        deployment = client.create_group(group_resource)
        emitter.publish('Created deployment {}'.format(deployment))

        return 0

    def remove(self, app_id, force):
        """
        :param app_id: ID of the app to remove
        :type app_id: str
        :param force: Whether to override running deployments.
        :type force: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        client.remove_app(app_id, force)
        return 0

    def group_remove(self, group_id, force):
        """
        :param group_id: ID of the app to remove
        :type group_id: str
        :param force: Whether to override running deployments.
        :type force: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        client.remove_group(group_id, force)
        return 0

    def show(self, app_id, version):
        """Show details of a Marathon application.

        :param app_id: The id for the application
        :type app_id: str
        :param version: The version, either absolute (date-time) or relative
        :type version: str
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()

        if version is not None:
            version = _calculate_version(client, app_id, version)

        app = client.get_app(app_id, version=version)

        emitter.publish(app)
        return 0

    def group_show(self, group_id, version=None):
        """Show details of a Marathon application.

        :param group_id: The id for the application
        :type group_id: str
        :param version: The version, either absolute (date-time) or relative
        :type version: str
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()

        app = client.get_group(group_id, version=version)

        emitter.publish(app)
        return 0

    def group_update(self, group_id, properties, force):
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

        client = self._create_marathon_client()

        # Ensure that the group exists
        client.get_group(group_id)

        resource = self._resource_reader.\
            get_resource_from_properties(properties)
        deployment = client.update_group(group_id, resource, force)

        emitter.publish('Created deployment {}'.format(deployment))
        return 0

    def start(self, app_id, instances, force):
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
        client = self._create_marathon_client()

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

    def stop(self, app_id, force):
        """Stop a Marathon application

        :param app_id: the id of the application
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: process return code
        :rtype: int
        """

        # Check that the application exists
        client = self._create_marathon_client()

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

    def update(self, app_id, properties, force):
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

        client = self._create_marathon_client()

        # Ensure that the application exists
        client.get_app(app_id)

        resource = self._resource_reader.\
            get_resource_from_properties(properties)
        deployment = client.update_app(app_id, resource, force)

        emitter.publish('Created deployment {}'.format(deployment))
        return 0

    def group_scale(self, group_id, scale_factor, force):
        """
        :param group_id: the id of the group
        :type group_id: str
        :param scale_factor: scale factor for application group
        :type scale_factor: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        scale_factor = util.parse_float(scale_factor)
        deployment = client.scale_group(group_id, scale_factor, force)
        emitter.publish('Created deployment {}'.format(deployment))
        return 0

    def restart(self, app_id, force):
        """
        :param app_id: the id of the application
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()

        desc = client.get_app(app_id)

        if desc['instances'] <= 0:
            app_id = util.normalize_marathon_id_path(app_id)
            emitter.publish(
                'Unable to perform rolling restart of application {!r} '
                'because it has no running tasks'.format(
                    app_id,
                    desc['instances']))
            return 1

        payload = client.restart_app(app_id, force)

        message = 'Created deployment {}'.format(payload['deploymentId'])
        emitter.publish(message)
        return 0

    def kill(self, app_id, scale, host):
        """
        :param app_id: the id of the application
        :type app_id: str
        :param scale: Scale the app down
        :type scale: bool
        :param host: Kill only those tasks running on host specified
        :type host: str
        :returns: process return code
        :rtype: int
        """
        client = self._create_marathon_client()

        payload = client.kill_tasks(app_id, host=host, scale=scale)
        # If scale is provided, the API return a "deploymentResult"
        # https://github.com/mesosphere/marathon/blob/50366c8/src/main/scala/mesosphere/marathon/api/RestResource.scala#L34-L36
        if scale:
            emitter.publish("Started deployment: {}".format(payload))
        else:
            if 'tasks' in payload:
                emitter.publish('Killed tasks: {}'.format(payload['tasks']))
                if len(payload['tasks']) == 0:
                    return 1
            else:
                emitter.publish('Killed tasks: []')
                return 1
        return 0

    def version_list(self, app_id, max_count):
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

        client = self._create_marathon_client()

        versions = client.get_app_versions(app_id, max_count)

        emitter.publish(versions)
        return 0

    def deployment_list(self, app_id, json_):
        """
        :param app_id: the application id
        :type app_id: str
        :param json_: output json if True
        :type json_: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()

        deployments = client.get_deployments(app_id)

        if not deployments and not json_:
            msg = "There are no deployments"
            if app_id:
                msg += " for '{}'".format(app_id)
            raise DCOSException(msg)

        emitting.publish_table(emitter,
                               deployments,
                               tables.deployment_table,
                               json_)
        return 0

    def deployment_stop(self, deployment_id):
        """
        :param deployment_id: the application id
        :type deployment_id: str
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        client.stop_deployment(deployment_id)

        return 0

    def deployment_rollback(self, deployment_id):
        """
        :param deployment_id: the application id
        :type deployment_id: str
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        deployment = client.rollback_deployment(deployment_id)

        emitter.publish(deployment)
        return 0

    def deployment_watch(self, deployment_id, max_count, interval):
        """
        :param deployment_id: the application id
        :type deployment_id: str
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

        client = self._create_marathon_client()

        count = 0
        while max_count is None or count < max_count:
            deployment = client.get_deployment(deployment_id)

            if deployment is None:
                return 0
            if util.is_windows_platform():
                os.system('cls')
            else:
                if 'TERM' in os.environ:
                    os.system('clear')
            emitter.publish('Deployment update time: '
                            '{} \n'.format(time.strftime("%Y-%m-%d %H:%M:%S",
                                                         time.gmtime())))
            emitter.publish(deployment)
            time.sleep(interval)
            count += 1

        return 0

    def task_list(self, app_id, json_):
        """
        :param app_id: the id of the application
        :type app_id: str
        :param json_: output json if True
        :type json_: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        tasks = client.get_tasks(app_id)

        emitting.publish_table(emitter, tasks, tables.app_task_table, json_)
        return 0

    def task_stop(self, task_id, wipe):
        """Stop a Marathon task

        :param task_id: the id of the task
        :type task_id: str
        :param wipe: whether to wipe persistent data and unreserve resources
        :type wipe: bool
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        task = client.stop_task(task_id, wipe)

        if task is None:
            raise DCOSException("Task '{}' does not exist".format(task_id))

        emitter.publish(task)
        return 0

    def task_show(self, task_id):
        """
        :param task_id: the task id
        :type task_id: str
        :returns: process return code
        :rtype: int
        """

        client = self._create_marathon_client()
        task = client.get_task(task_id)

        if task is None:
            raise DCOSException("Task '{}' does not exist".format(task_id))

        emitter.publish(task)
        return 0

    def pod_add(self, pod_resource_path):
        """
        :param pod_resource_path: optional file path for the pod resource
        :type pod_resource_path: str
        :returns: process return code
        :rtype: int
        """

        marathon_client = self._create_marathon_client()
        self._ensure_pods_support(marathon_client)

        pod_json = self._resource_reader.get_resource(pod_resource_path)
        deployment = marathon_client.add_pod(pod_json)
        emitter.publish('Created deployment {}'.format(deployment))
        return 0

    def pod_remove(self, pod_id, force):
        """
        :param pod_id: the Marathon ID of the pod to remove
        :type pod_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: process return code
        :rtype: int
        """

        marathon_client = self._create_marathon_client()
        self._ensure_pods_support(marathon_client)

        marathon_client.remove_pod(pod_id, force)
        return 0

    def pod_list(self, json_):
        """
        :param json_: output JSON if true
        :type json_: bool
        :returns: process return code
        :rtype: int
        """

        marathon_client = self._create_marathon_client()
        self._ensure_pods_support(marathon_client)

        pods = marathon_client.list_pod()
        emitting.publish_table(emitter, pods, tables.pod_table, json_)
        return 0

    def pod_show(self, pod_id):
        """Show details of a Marathon pod.

        :param pod_id: the Marathon ID of the pod to show
        :type pod_id: str
        :returns: process return code
        :rtype: int
        """

        marathon_client = self._create_marathon_client()
        self._ensure_pods_support(marathon_client)

        pod_json = marathon_client.show_pod(pod_id)
        emitter.publish(pod_json)
        return 0

    def pod_update(self, pod_id, force):
        """
        :param pod_id: the Marathon ID of the pod to update
        :type pod_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: process return code
        :rtype: int
        """

        marathon_client = self._create_marathon_client()
        self._ensure_pods_support(marathon_client)

        # Ensure that the pod exists
        marathon_client.show_pod(pod_id)

        resource = self._resource_reader.get_resource(name=None)
        deployment_id = marathon_client.update_pod(
            pod_id, pod_json=resource, force=force)

        emitter.publish('Created deployment {}'.format(deployment_id))
        return 0

    def pod_kill(self, pod_id, instance_ids):
        """
        :param pod_id: the Marathon ID of the pod to kill instances from
        :type pod_id: str
        :param instance_ids: the instance IDs to kill
        :type instance_ids: [str]
        :returns: process return code
        :rtype: int
        """

        if not instance_ids:
            raise DCOSException('Please provide at least one pod instance ID')

        marathon_client = self._create_marathon_client()
        self._ensure_pods_support(marathon_client)

        marathon_client.kill_pod_instances(pod_id, instance_ids)
        return 0

    @staticmethod
    def _ensure_pods_support(marathon_client):
        """Raises an exception if the given client is communicating with a
        version of Marathon that doesn't support pods.

        :param marathon_client: the Marathon client to check
        :type marathon_client: dcos.marathon.Client
        :rtype: None
        """

        if not marathon_client.pod_feature_supported():
            msg = 'This command is not supported by your version of Marathon'
            raise DCOSException(msg)


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
        logger.exception('Unable to parse version %s', version)
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
            'dcos',
            'data/config-schema/marathon.json').decode('utf-8'))
