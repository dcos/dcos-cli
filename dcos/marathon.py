import json
from distutils.version import LooseVersion

from dcos import http, util
from dcos.errors import DCOSException

from six.moves import urllib

logger = util.get_logger(__name__)


def create_client(config=None):
    """Creates a Marathon client with the supplied configuration.

    :param config: configuration dictionary
    :type config: config.Toml
    :returns: Marathon client
    :rtype: dcos.marathon.Client
    """

    if config is None:
        config = util.get_config()

    marathon_url = _get_marathon_url(config)

    if 'marathon.username' in config:
        http.auth = (config.get('marathon.username'), config.get('marathon.password'))

    logger.info('Creating marathon client with: %r', marathon_url)
    return Client(marathon_url)


def _get_marathon_url(config):
    """
    :param config: configuration dictionary
    :type config: config.Toml
    :returns: marathon base url
    :rtype: str
    """

    marathon_url = config.get('marathon.url')
    if marathon_url is None:
        dcos_url = util.get_config_vals(config, ['core.dcos_url'])[0]
        marathon_url = urllib.parse.urljoin(dcos_url, 'marathon/')

    return marathon_url


def _to_exception(response):
    """
    :param response: HTTP response object or Exception
    :type response: requests.Response | Exception
    :returns: An exception with the message from the response JSON
    :rtype: Exception
    """

    if isinstance(response, Exception):
        return DCOSException(_default_marathon_error(str(response)))

    message = response.json().get('message')
    if message is None:
        errs = response.json().get('errors')
        if errs is None:
            logger.error(
                'Marathon server did not return a message: %s',
                response.json())
            return DCOSException(_default_marathon_error())

        msg = '\n'.join(error['error'] for error in errs)
        return DCOSException(_default_marathon_error(msg))

    return DCOSException('Error: {}'.format(response.json()['message']))


class Client(object):
    """Class for talking to the Marathon server.

    :param marathon_url: the base URL for the Marathon server
    :type marathon_url: str
    """

    def __init__(self, marathon_url):
        self._base_url = marathon_url

        min_version = "0.8.1"
        version = LooseVersion(self.get_about()["version"])
        self._version = version
        if version < LooseVersion(min_version):
            msg = ("The configured Marathon with version {0} is outdated. " +
                   "Please use version {1} or later.").format(
                       version,
                       min_version)
            raise DCOSException(msg)

    def _create_url(self, path):
        """Creates the url from the provided path.
        :param path: url path
        :type path: str
        :returns: constructed url
        :rtype: str
        """

        return urllib.parse.urljoin(self._base_url, path)

    def get_version(self):
        """Get marathon version
        :returns: marathon version
        rtype: LooseVersion
        """

        return self._version

    def get_about(self):
        """Returns info about Marathon instance

        :returns Marathon information
        :rtype: dict
        """

        url = self._create_url('v2/info')

        response = http.get(url, to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

        return response.json()['apps']

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

        response = http.post(url,
                             json=app_json,
                             to_exception=_to_exception)

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

        response = http.put(url,
                            params=params,
                            json=payload,
                            to_exception=_to_exception)

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
        :rtype: bool
        """

        app_id = self.normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}'.format(app_id))

        response, error = http.put(url,
                                   params=params,
                                   json={'instances': int(instances)},
                                   to_exception=_to_exception)

        if error is not None:
            return (None, error)

        deployment = response.json()['deploymentId']
        return (deployment, None)

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

        http.delete(url, params=params, to_exception=_to_exception)

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

        http.delete(url, params=params, to_exception=_to_exception)

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

        response = http.post(url,
                             params=params,
                             to_exception=_to_exception)

        return response.json()

    def get_deployment(self, deployment_id):
        """Returns a deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :returns: a deployment
        :rtype: dict
        """

        url = self._create_url('v2/deployments')

        response = http.get(url,
                            to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

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

        response = http.delete(
            url,
            params=params,
            to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

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

        response = http.get(url, to_exception=_to_exception)

        task = next(
            (task for task in response.json()['tasks']
             if task_id == task['id']),
            None)

        return task

    def get_app_schema(self):
        """Returns app json schema

        :returns: application json schema
        :rtype: json schema or None if endpoint doesn't exist
        """

        version = self.get_version()
        schema_version = LooseVersion("0.9.0")
        if version < schema_version:
            return None

        url = self._create_url('v2/schemas/app')
        response = http.get(url)

        return response.json()

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

        response = http.post(url, json=group_json, to_exception=_to_exception)

        return response.json()


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
