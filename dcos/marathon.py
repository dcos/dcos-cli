import json

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

    logger.info('Creating marathon client with: %r', marathon_url)
    return Client(marathon_url, timeout=timeout)


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


def _to_exception(response):
    """
    :param response: HTTP response object or Exception
    :type response: requests.Response | Exception
    :returns: An exception with the message from the response JSON
    :rtype: Exception
    """

    if response.status_code == 400:
        msg = 'Error on request [{0} {1}]: HTTP {2}: {3}'.format(
            response.request.method,
            response.request.url,
            response.status_code,
            response.reason)

        # Marathon is buggy and sometimes return JSON, and sometimes
        # HTML.  We only include the error message if it's JSON.
        try:
            json_msg = response.json()
            msg += ':\n' + json.dumps(json_msg,
                                      indent=2,
                                      sort_keys=True,
                                      separators=(',', ': '))
        except ValueError:
            pass

        return DCOSException(msg)
    elif response.status_code == 409:
        return DCOSException(
            'App or group is locked by one or more deployments. '
            'Override with --force.')

    try:
        response_json = response.json()
    except Exception:
        logger.exception(
            'Unable to decode response body as a JSON value: %r',
            response)

        return DCOSException(
            'Error decoding response from [{0}]: HTTP {1}: {2}'.format(
                response.request.url, response.status_code, response.reason))
    message = response_json.get('message')
    if message is None:
        errs = response_json.get('errors')
        if errs is None:
            logger.error(
                'Marathon server did not return a message: %s',
                response_json)
            return DCOSException(_default_marathon_error())

        msg = '\n'.join(error['error'] for error in errs)
        return DCOSException(_default_marathon_error(msg))

    return DCOSException('Error: {}'.format(message))


def _http_req(fn, *args, **kwargs):
    """Make an HTTP request, and raise a marathon-specific exception for
    HTTP error codes.

    :param fn: function to call
    :type fn: function
    :param args: args to pass to `fn`
    :type args: [object]
    :param kwargs: kwargs to pass to `fn`
    :type kwargs: dict
    :returns: `fn` return value
    :rtype: object

    """
    try:
        return fn(*args, **kwargs)
    except DCOSHTTPException as e:
        raise _to_exception(e.response)


class Client(object):
    """Class for talking to the Marathon server.

    :param marathon_url: the base URL for the Marathon server
    :type marathon_url: str
    """

    def __init__(self, marathon_url, timeout=http.DEFAULT_TIMEOUT):
        self._base_url = marathon_url
        self._timeout = timeout

    def _create_url(self, path):
        """Creates the url from the provided path.
        :param path: url path
        :type path: str
        :returns: constructed url
        :rtype: str
        """

        return urllib.parse.urljoin(self._base_url, path)

    def get_about(self):
        """Returns info about Marathon instance

        :returns Marathon information
        :rtype: dict
        """

        url = self._create_url('v2/info')
        response = _http_req(http.get, url, timeout=self._timeout)

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

        app_id = self.normalize_app_id(app_id)
        if version is None:
            url = self._create_url('v2/apps{}'.format(app_id))
        else:
            url = self._create_url(
                'v2/apps{}/versions/{}'.format(app_id, version))

        response = _http_req(http.get, url, timeout=self._timeout)

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

        url = self._create_url('v2/groups')
        response = _http_req(http.get, url, timeout=self._timeout)
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

        group_id = self.normalize_app_id(group_id)
        if version is None:
            url = self._create_url('v2/groups{}'.format(group_id))
        else:
            url = self._create_url(
                'v2/groups{}/versions/{}'.format(group_id, version))

        response = _http_req(http.get, url, timeout=self._timeout)
        return response.json()

    def get_app_versions(self, app_id, max_count=None):
        """Asks Marathon for all the versions of the Application up to a
        maximum count.

        :param app_id: the ID of the application or group
        :type app_id: str
        :param id_type: type of the id ("apps" or "groups")
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

        app_id = self.normalize_app_id(app_id)

        url = self._create_url('v2/apps{}/versions'.format(app_id))

        response = _http_req(http.get, url, timeout=self._timeout)

        if max_count is None:
            return response.json()['versions']
        else:
            return response.json()['versions'][:max_count]

    def get_apps(self):
        """Get a list of known applications.

        :returns: list of known applications
        :rtype: [dict]
        """

        url = self._create_url('v2/apps')
        response = _http_req(http.get, url, timeout=self._timeout)
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

        url = self._create_url('v2/apps')

        # The file type exists only in Python 2, preventing type(...) is file.
        if hasattr(app_resource, 'read'):
            app_json = json.load(app_resource)
        else:
            app_json = app_resource

        response = _http_req(http.post, url,
                             json=app_json,
                             timeout=self._timeout)

        return response.json()

    def _update(self, resource_id, payload, force=None, url_endpoint="apps"):
        """Update an application or group.

        :param resource_id: the app or group id
        :type resource_id: str
        :param payload: the json payload
        :type payload: dict
        :param force: whether to override running deployments
        :type force: bool
        :param url_endpoint: resource type to update ("apps" or "groups")
        :type url_endpoint: str
        :returns: the resulting deployment ID
        :rtype: str
        """

        resource_id = self.normalize_app_id(resource_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/{}{}'.format(url_endpoint, resource_id))

        response = _http_req(http.put, url,
                             params=params,
                             json=payload,
                             timeout=self._timeout)

        return response.json().get('deploymentId')

    def update_app(self, app_id, payload, force=None):
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

        return self._update(app_id, payload, force)

    def update_group(self, group_id, payload, force=None):
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

        return self._update(group_id, payload, force, "groups")

    def scale_app(self, app_id, instances, force=None):
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

        app_id = self.normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}'.format(app_id))

        response = _http_req(http.put,
                             url,
                             params=params,
                             json={'instances': int(instances)},
                             timeout=self._timeout)

        deployment = response.json()['deploymentId']
        return deployment

    def scale_group(self, group_id, scale_factor, force=None):
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

        group_id = self.normalize_app_id(group_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/groups{}'.format(group_id))

        response = http.put(url,
                            params=params,
                            json={'scaleBy': scale_factor},
                            timeout=self._timeout)

        deployment = response.json()['deploymentId']
        return deployment

    def stop_app(self, app_id, force=None):
        """Scales an application to zero instances.

        :param app_id: the ID of the application to stop
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: bool
        """

        return self.scale_app(app_id, 0, force)

    def remove_app(self, app_id, force=None):
        """Completely removes the requested application.

        :param app_id: the ID of the application to remove
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :rtype: None
        """

        app_id = self.normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}'.format(app_id))
        _http_req(http.delete, url, params=params, timeout=self._timeout)

    def remove_group(self, group_id, force=None):
        """Completely removes the requested application.

        :param group_id: the ID of the application to remove
        :type group_id: str
        :param force: whether to override running deployments
        :type force: bool
        :rtype: None
        """

        group_id = self.normalize_app_id(group_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/groups{}'.format(group_id))

        _http_req(http.delete, url, params=params, timeout=self._timeout)

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
        app_id = self.normalize_app_id(app_id)
        if host:
            params['host'] = host
        if scale:
            params['scale'] = scale
        url = self._create_url('v2/apps{}/tasks'.format(app_id))
        response = _http_req(http.delete, url,
                             params=params,
                             timeout=self._timeout)
        return response.json()

    def restart_app(self, app_id, force=None):
        """Performs a rolling restart of all of the tasks.

        :param app_id: the id of the application to restart
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: the deployment id and version
        :rtype: dict
        """

        app_id = self.normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}/restart'.format(app_id))

        response = _http_req(http.post, url,
                             params=params,
                             timeout=self._timeout)
        return response.json()

    def get_deployment(self, deployment_id):
        """Returns a deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :returns: a deployment
        :rtype: dict
        """

        url = self._create_url('v2/deployments')

        response = _http_req(http.get, url, timeout=self._timeout)
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

        url = self._create_url('v2/deployments')

        response = _http_req(http.get, url, timeout=self._timeout)

        if app_id is not None:
            app_id = self.normalize_app_id(app_id)
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

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/deployments/{}'.format(deployment_id))

        response = _http_req(http.delete, url,
                             params=params,
                             timeout=self._timeout)

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

        url = self._create_url('v2/tasks')

        response = _http_req(http.get, url, timeout=self._timeout)

        if app_id is not None:
            app_id = self.normalize_app_id(app_id)
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

        url = self._create_url('v2/tasks')

        response = _http_req(http.get, url, timeout=self._timeout)

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

        url = self._create_url('v2/tasks/delete')

        response = _http_req(http.post,
                             url,
                             params=params,
                             json={'ids': [task_id]},
                             timeout=self._timeout)

        task = next(
            (task for task in response.json()['tasks']
             if task_id == task['id']),
            None)

        return task

    def normalize_app_id(self, app_id):
        """Normalizes the application id.

        :param app_id: raw application ID
        :type app_id: str
        :returns: normalized application ID
        :rtype: str
        """

        return urllib.parse.quote('/' + app_id.strip('/'))

    def create_group(self, group_resource):
        """Add a new group.

        :param group_resource: grouplication resource
        :type group_resource: dict, bytes or file
        :returns: the group description
        :rtype: dict
        """
        url = self._create_url('v2/groups')

        # The file type exists only in Python 2, preventing type(...) is file.
        if hasattr(group_resource, 'read'):
            group_json = json.load(group_resource)
        else:
            group_json = group_resource

        response = _http_req(http.post, url,
                             json=group_json,
                             timeout=self._timeout)
        return response.json()

    def get_leader(self):
        """ Get the leading marathon instance.

        :returns: string of the form <ip>:<port>
        :rtype: str
        """

        url = self._create_url('v2/leader')
        response = _http_req(http.get, url, timeout=self._timeout)
        return response.json()['leader']


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
