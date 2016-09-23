import json
import jsonschema
import pkg_resources

from dcos import config, http, util
from dcos.errors import DCOSException, DCOSHTTPException

from six.moves import urllib

logger = util.get_logger(__name__)


def create_client(toml_config=None):
    """Creates a Marathon client with the supplied configuration.

    :param toml_config: configuration dictionary
    :type toml_config: config.Toml
    :returns: Marathon client
    :rtype: dcos.marathon.Client
    """

    if toml_config is None:
        toml_config = config.get_config()

    marathon_url = _get_marathon_url(toml_config)
    timeout = config.get_config_val('core.timeout') or http.DEFAULT_TIMEOUT
    rpc_client = RpcClient(marathon_url, timeout)

    logger.info('Creating marathon client with: %r', marathon_url)
    return Client(rpc_client)


def _get_marathon_url(toml_config):
    """
    :param toml_config: configuration dictionary
    :type toml_config: config.Toml
    :returns: marathon base url
    :rtype: str
    """

    marathon_url = config.get_config_val('marathon.url', toml_config)
    if marathon_url is None:
        dcos_url = config.get_config_val('core.dcos_url', toml_config)
        if dcos_url is None:
            raise config.missing_config_exception(['core.dcos_url'])
        marathon_url = urllib.parse.urljoin(dcos_url, 'service/marathon/')

    return marathon_url


def load_error_json_schema():
    """Reads and parses Marathon error response JSON schema from file

    :returns: the parsed JSON schema
    :rtype: dict
    """
    schema_path = 'data/marathon/error.schema.json'
    schema_bytes = pkg_resources.resource_string('dcos', schema_path)
    return json.loads(schema_bytes.decode('utf-8'))


class RpcClient(object):
    """Convenience class for making requests against a common RPC API.

    For example, it ensures the same base URL is used for all requests. This
    class is also useful as a target for mocks in unit tests, because it
    presents a minimal, application-focused interface.

    :param base_url: the URL prefix to use for all requests
    :type base_url: str
    :param timeout: number of seconds to wait for a response
    :type timeout: float
    """

    def __init__(self, base_url, timeout=http.DEFAULT_TIMEOUT):
        if not base_url.endswith('/'):
            base_url += '/'
        self._base_url = base_url
        self._timeout = timeout

    ERROR_JSON_VALIDATOR = jsonschema.Draft4Validator(load_error_json_schema())

    @classmethod
    def response_error_message(cls, status_code, reason, request_method,
                               request_url, json_body):
        """Renders a human-readable error message from the given response data.

        :param status_code: the integer status code from an HTTP response
        :type status_code: int
        :param reason: human-readable text representation of the status code
        :type reason: str
        :param request_method: the HTTP method used for the request
        :type request_method: str
        :param request_url: the URL the request was sent to
        :type request_url: str
        :param json_body: the response body, parsed as JSON, or None if
                          parsing failed
        :type json_body: dict | list | str | int | bool | None
        :return: the rendered error message
        :rtype: str
        """

        if status_code == 400:
            template = 'Error on request [{} {}]: HTTP 400: {}{}'
            suffix = ''
            if json_body is not None:
                json_str = json.dumps(json_body, indent=2, sort_keys=True)
                suffix = ':\n' + json_str
            return template.format(request_method, request_url, reason, suffix)

        if status_code == 409:
            return ('App, group, or pod is locked by one or more deployments. '
                    'Override with --force.')

        if json_body is None:
            template = 'Error decoding response from [{}]: HTTP {}: {}'
            return template.format(request_url, status_code, reason)

        if not cls.ERROR_JSON_VALIDATOR.is_valid(json_body):
            log_str = 'Marathon server did not return a message: %s'
            logger.error(log_str, json_body)

            return _default_marathon_error()

        message = json_body.get('message')
        if message is None:
            message = '\n'.join(err['error'] for err in json_body['errors'])
            return _default_marathon_error(message)

        return 'Error: {}'.format(message)

    def http_req(self, method_fn, path, *args, **kwargs):
        """Make an HTTP request, and raise a marathon-specific exception for
        HTTP error codes.

        :param method_fn: function to call that invokes a specific HTTP method
        :type method_fn: function
        :param path: the endpoint path to append to this object's base URL
        :type path: str
        :param args: additional args to pass to `method_fn`
        :type args: [object]
        :param kwargs: kwargs to pass to `method_fn`
        :type kwargs: dict
        :returns: `method_fn` return value
        :rtype: requests.Response
        """
        url = self._base_url + path.lstrip('/')

        if 'timeout' not in kwargs:
            kwargs['timeout'] = self._timeout

        try:
            return method_fn(url, *args, **kwargs)
        except DCOSHTTPException as e:
            # Marathon is buggy and sometimes returns JSON, sometimes returns
            # HTML. We only include the body in the error message if it's JSON.
            try:
                json_body = e.response.json()
            except:
                logger.exception(
                    'Unable to decode response body as a JSON value: %r',
                    e.response)

                json_body = None

            message = RpcClient.response_error_message(
                status_code=e.response.status_code,
                reason=e.response.reason,
                request_method=e.response.request.method,
                request_url=e.response.request.url,
                json_body=json_body)
            raise DCOSException(message)


class Client(object):
    """Class for talking to the Marathon server.

    :param rpc_client: provides a method for making HTTP requests
    :type rpc_client: _RpcClient
    """

    def __init__(self, rpc_client):
        self._rpc = rpc_client

    def get_about(self):
        """Returns info about Marathon instance

        :returns Marathon information
        :rtype: dict
        """

        response = self._rpc.http_req(http.get, 'v2/info')

        return response.json()

    def get_app(self, app_id, version=None):
        """Returns a representation of the requested application version. If
        version is None the return the latest version.

        :param app_id: the ID of the application
        :type app_id: str
        :param version: application version as a ISO8601 datetime
        :type version: str
        :returns: the requested Marathon application
        :rtype: dict
        """

        app_id = util.normalize_marathon_id_path(app_id)
        if version is None:
            path = 'v2/apps{}'.format(app_id)
        else:
            path = 'v2/apps{}/versions/{}'.format(app_id, version)

        response = self._rpc.http_req(http.get, path)

        # Looks like Marathon return different JSON for versions
        if version is None:
            return response.json()['app']
        else:
            return response.json()

    def get_groups(self):
        """Get a list of known groups.

        :returns: list of known groups
        :rtype: list of dict
        """

        response = self._rpc.http_req(http.get, 'v2/groups')
        return response.json()['groups']

    def get_group(self, group_id, version=None):
        """Returns a representation of the requested group version. If
        version is None the return the latest version.

        :param group_id: the ID of the application
        :type group_id: str
        :param version: application version as a ISO8601 datetime
        :type version: str
        :returns: the requested Marathon application
        :rtype: dict
        """

        group_id = util.normalize_marathon_id_path(group_id)
        if version is None:
            path = 'v2/groups{}'.format(group_id)
        else:
            path = 'v2/groups{}/versions/{}'.format(group_id, version)

        response = self._rpc.http_req(http.get, path)
        return response.json()

    def get_app_versions(self, app_id, max_count=None):
        """Asks Marathon for all the versions of the Application up to a
        maximum count.

        :param app_id: the ID of the application or group
        :type app_id: str
        :param max_count: the maximum number of version to fetch
        :type max_count: int
        :returns: a list of all the version of the application
        :rtype: [str]
        """

        if max_count is not None and max_count <= 0:
            raise DCOSException(
                'Maximum count must be a positive number: {}'.format(max_count)
            )

        app_id = util.normalize_marathon_id_path(app_id)

        path = 'v2/apps{}/versions'.format(app_id)

        response = self._rpc.http_req(http.get, path)

        if max_count is None:
            return response.json()['versions']
        else:
            return response.json()['versions'][:max_count]

    def get_apps(self):
        """Get a list of known applications.

        :returns: list of known applications
        :rtype: [dict]
        """

        response = self._rpc.http_req(http.get, 'v2/apps')
        return response.json()['apps']

    def get_apps_for_framework(self, framework_name):
        """ Return all apps running the given framework.

        :param framework_name: framework name
        :type framework_name: str
        :rtype: [dict]
        """

        return [app for app in self.get_apps()
                if app.get('labels', {}).get(
                    'DCOS_PACKAGE_FRAMEWORK_NAME') == framework_name]

    def add_app(self, app_resource):
        """Add a new application.

        :param app_resource: application resource
        :type app_resource: dict, bytes or file
        :returns: the application description
        :rtype: dict
        """

        # The file type exists only in Python 2, preventing type(...) is file.
        if hasattr(app_resource, 'read'):
            app_json = json.load(app_resource)
        else:
            app_json = app_resource

        response = self._rpc.http_req(http.post, 'v2/apps', json=app_json)

        return response.json()

    def _update(self, resource_type, resource_id, resource_json, force=False):
        """Update an application, group, or pod.

        :param resource_type: one of 'apps', 'groups', or 'pods'
        :type resource_type: str
        :param resource_id: the app, group, or pod ID
        :type resource_id: str
        :param resource_json: the json payload
        :type resource_json: {}
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: str
        """

        path_prefix = 'v2/{}'.format(resource_type)
        path = self._marathon_id_path_join(path_prefix, resource_id)
        params = self._force_params(force)
        response = self._rpc.http_req(
            http.put, path, params=params, json=resource_json)
        body_json = self._parse_json(response)

        try:
            return body_json['deploymentId']
        except KeyError:
            template = ('Error: missing "deploymentId" field in the following '
                        'JSON response from Marathon:\n{}')
            rendered_json = json.dumps(body_json, indent=2, sort_keys=True)
            raise DCOSException(template.format(rendered_json))

    def update_app(self, app_id, payload, force=False):
        """Update an application.

        :param app_id: the application id
        :type app_id: str
        :param payload: the json payload
        :type payload: dict
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: str
        """

        return self._update('apps', app_id, payload, force)

    def update_group(self, group_id, payload, force=False):
        """Update a group.

        :param group_id: the group id
        :type group_id: str
        :param payload: the json payload
        :type payload: dict
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: str
        """

        return self._update('groups', group_id, payload, force)

    def scale_app(self, app_id, instances, force=False):
        """Scales an application to the requested number of instances.

        :param app_id: the ID of the application to scale
        :type app_id: str
        :param instances: the requested number of instances
        :type instances: int
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: str
        """

        app_id = util.normalize_marathon_id_path(app_id)
        params = self._force_params(force)
        path = 'v2/apps{}'.format(app_id)

        response = self._rpc.http_req(http.put,
                                      path,
                                      params=params,
                                      json={'instances': int(instances)})

        deployment = response.json()['deploymentId']
        return deployment

    def scale_group(self, group_id, scale_factor, force=False):
        """Scales a group with the requested scale-factor.
        :param group_id: the ID of the group to scale
        :type group_id: str
        :param scale_factor: the requested value of scale-factor
        :type scale_factor: float
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: bool
        """

        group_id = util.normalize_marathon_id_path(group_id)
        params = self._force_params(force)
        path = 'v2/groups{}'.format(group_id)

        response = self._rpc.http_req(http.put,
                                      path,
                                      params=params,
                                      json={'scaleBy': scale_factor})

        deployment = response.json()['deploymentId']
        return deployment

    def stop_app(self, app_id, force=False):
        """Scales an application to zero instances.

        :param app_id: the ID of the application to stop
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: bool
        """

        return self.scale_app(app_id, 0, force)

    def remove_app(self, app_id, force=False):
        """Completely removes the requested application.

        :param app_id: the ID of the application to remove
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :rtype: None
        """

        app_id = util.normalize_marathon_id_path(app_id)
        params = self._force_params(force)
        path = 'v2/apps{}'.format(app_id)
        self._rpc.http_req(http.delete, path, params=params)

    def remove_group(self, group_id, force=False):
        """Completely removes the requested application.

        :param group_id: the ID of the application to remove
        :type group_id: str
        :param force: whether to override running deployments
        :type force: bool
        :rtype: None
        """

        group_id = util.normalize_marathon_id_path(group_id)
        params = self._force_params(force)
        path = 'v2/groups{}'.format(group_id)

        self._rpc.http_req(http.delete, path, params=params)

    def kill_tasks(self, app_id, scale=None, host=None):
        """Kills the tasks for a given application,
        and can target a given agent, with a future target scale

        :param app_id: the id of the application to restart
        :type app_id: str
        :param scale: Scale the app down after killing the specified tasks
        :type scale: bool
        :param host: host to target restarts on
        :type host: string
        """
        params = {}
        app_id = util.normalize_marathon_id_path(app_id)
        if host:
            params['host'] = host
        if scale:
            params['scale'] = scale
        path = 'v2/apps{}/tasks'.format(app_id)
        response = self._rpc.http_req(http.delete, path, params=params)
        return response.json()

    def restart_app(self, app_id, force=False):
        """Performs a rolling restart of all of the tasks.

        :param app_id: the id of the application to restart
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: the deployment id and version
        :rtype: dict
        """

        app_id = util.normalize_marathon_id_path(app_id)
        params = self._force_params(force)
        path = 'v2/apps{}/restart'.format(app_id)

        response = self._rpc.http_req(http.post, path, params=params)
        return response.json()

    def get_deployment(self, deployment_id):
        """Returns a deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :returns: a deployment
        :rtype: dict
        """

        response = self._rpc.http_req(http.get, 'v2/deployments')
        deployment = next(
            (deployment for deployment in response.json()
             if deployment_id == deployment['id']),
            None)

        return deployment

    def get_deployments(self, app_id=None):
        """Returns a list of deployments, optionally limited to an app.

        :param app_id: the id of the application
        :type app_id: str
        :returns: a list of deployments
        :rtype: list of dict
        """

        response = self._rpc.http_req(http.get, 'v2/deployments')

        if app_id is not None:
            app_id = util.normalize_marathon_id_path(app_id)
            deployments = [
                deployment for deployment in response.json()
                if app_id in deployment['affectedApps']
            ]
        else:
            deployments = response.json()

        return deployments

    def _cancel_deployment(self, deployment_id, force):
        """Cancels an application deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :param force: if set to `False`, stop the deployment and
                      create a new rollback deployment to reinstate the
                      previous configuration. If set to `True`, simply stop the
                      deployment.
        :type force: bool
        :returns: cancelation deployment
        :rtype: dict
        """

        params = self._force_params(force)
        path = 'v2/deployments/{}'.format(deployment_id)

        response = self._rpc.http_req(http.delete, path, params=params)

        if force:
            return None
        else:
            return response.json()

    def rollback_deployment(self, deployment_id):
        """Rolls back an application deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :returns: cancelation deployment
        :rtype: dict
        """

        return self._cancel_deployment(deployment_id, False)

    def stop_deployment(self, deployment_id):
        """Stops an application deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :rtype: None
        """

        self._cancel_deployment(deployment_id, True)

    def get_tasks(self, app_id):
        """Returns a list of tasks, optionally limited to an app.

        :param app_id: the id of the application to restart
        :type app_id: str
        :returns: a list of tasks
        :rtype: [dict]
        """

        response = self._rpc.http_req(http.get, 'v2/tasks')

        if app_id is not None:
            app_id = util.normalize_marathon_id_path(app_id)
            tasks = [
                task for task in response.json()['tasks']
                if app_id == task['appId']
            ]
        else:
            tasks = response.json()['tasks']

        return tasks

    def get_task(self, task_id):
        """Returns a task

        :param task_id: the id of the task
        :type task_id: str
        :returns: a tasks
        :rtype: dict
        """

        response = self._rpc.http_req(http.get, 'v2/tasks')

        task = next(
            (task for task in response.json()['tasks']
             if task_id == task['id']),
            None)

        return task

    def stop_task(self, task_id, wipe=None):
        """Stops a task.

        :param task_id: the ID of the task
        :type task_id: str
        :param wipe: whether remove reservations and persistent volumes.
        :type wipe: bool
        :returns: a tasks
        :rtype: dict
        """

        if not wipe:
            params = None
        else:
            params = {'wipe': 'true'}

        response = self._rpc.http_req(http.post,
                                      'v2/tasks/delete',
                                      params=params,
                                      json={'ids': [task_id]})

        task = next(
            (task for task in response.json()['tasks']
             if task_id == task['id']),
            None)

        return task

    def create_group(self, group_resource):
        """Add a new group.

        :param group_resource: grouplication resource
        :type group_resource: dict, bytes or file
        :returns: the group description
        :rtype: dict
        """

        # The file type exists only in Python 2, preventing type(...) is file.
        if hasattr(group_resource, 'read'):
            group_json = json.load(group_resource)
        else:
            group_json = group_resource

        response = self._rpc.http_req(http.post, 'v2/groups', json=group_json)
        return response.json()

    def get_leader(self):
        """ Get the leading marathon instance.

        :returns: string of the form <ip>:<port>
        :rtype: str
        """

        response = self._rpc.http_req(http.get, 'v2/leader')
        return response.json()['leader']

    def add_pod(self, pod_json):
        """Add a new pod.

        :param pod_json: JSON pod definition
        :type pod_json: dict
        :returns: description of created pod
        :rtype: dict
        """

        response = self._rpc.http_req(http.post, 'v2/pods', json=pod_json)
        return self._parse_json(response)

    def remove_pod(self, pod_id, force=False):
        """Completely removes the requested pod.

        :param pod_id: the ID of the pod to remove
        :type pod_id: str
        :param force: whether to override running deployments
        :type force: bool
        :rtype: None
        """

        path = self._marathon_id_path_join('v2/pods', pod_id)
        params = self._force_params(force)
        self._rpc.http_req(http.delete, path, params=params)

    def show_pod(self, pod_id):
        """Returns a representation of the requested pod.

        :param pod_id: the ID of the pod
        :type pod_id: str
        :returns: the requested Marathon pod
        :rtype: dict
        """

        path = self._marathon_id_path_join('v2/pods', pod_id)
        response = self._rpc.http_req(http.get, path)
        return self._parse_json(response)

    def list_pod(self):
        """Get a list of known pods.

        :returns: list of known pods
        :rtype: [dict]
        """

        response = self._rpc.http_req(http.get, 'v2/pods')
        return self._parse_json(response)

    def update_pod(self, pod_id, pod_json, force=False):
        """Update a pod.

        :param pod_id: the pod ID
        :type pod_id: str
        :param pod_json: JSON pod definition
        :type pod_json: {}
        :param force: whether to override running deployments
        :type force: bool
        :rtype: None
        """

        return self._update('pods', pod_id, pod_json, force)

    def pod_feature_supported(self):
        """Return whether or not this client is communicating with a server
        that supports pod operations.

        :rtype: bool
        """

        response = http.head('whatever')
        return response.status_code // 100 == 2

    @staticmethod
    def _marathon_id_path_join(url_path, id_path):
        """Concatenates a URL path with a Marathon "ID path", ensuring the
        result is well-formed.

        The path and the ID will be joined with a single forward slash (/),
        all trailing slashes in the ID will be removed, and the ID will have
        all URL-unsafe characters escaped, as if by urllib.parse.quote().

        :param url_path: the path portion of a URL
        :type url_path: str
        :param path_id: a Marathon "ID path", e.g. app ID or group ID
        :type path_id: str
        :returns: the path with the ID appended
        :rtype: str
        """

        normalized_id_path = urllib.parse.quote(id_path.strip('/'))
        return url_path.rstrip('/') + '/' + normalized_id_path

    @staticmethod
    def _force_params(force):
        """Returns the query parameters that signify the provided force value.

        :param force: whether to override running deployments
        :type force: bool
        :rtype: {} | None
        """

        return {'force': 'true'} if force else None

    @staticmethod
    def _parse_json(response):
        """Attempts to parse the body of the given response as JSON.

        Raises DCOSException if parsing fails.

        :param response: the response containing the body to parse
        :type response: requests.Response
        :return: the parsed JSON
        :rtype: {} | [] | str | int | float | bool | None
        """

        try:
            return response.json()
        except:
            template = ('Error: Response from Marathon was not in expected '
                        'JSON format:\n{}')
            raise DCOSException(template.format(response.text))


def _default_marathon_error(message=""):
    """
    :param message: additional message
    :type message: str
    :returns: marathon specific error message
    :rtype: str
    """

    return ("Marathon likely misconfigured. Please check your proxy or "
            "Marathon URL settings. See dcos config --help. {}").format(
                message)
