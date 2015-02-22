import json

import requests
from dcos.api import errors, util

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote

logger = util.get_logger(__name__)


def create_client(config):
    """Creates a Marathon client with the supplied configuration.

    :param config: configuration dictionary
    :type config: config.Toml
    :returns: Marathon client
    :rtype: dcos.api.marathon.Client
    """
    return Client(config['marathon.host'], config['marathon.port'])


class Client(object):
    """Class for talking to the Marathon server.

    :param host: host for the Marathon server
    :type host: str
    :param port: port for the Marathon server
    :type port: int
    """

    def __init__(self, host, port):
        self._url_pattern = "http://{host}:{port}/{path}"
        self._host = host
        self._port = port

    def _create_url(self, path, query_params=None):
        """Creates the url from the provided path.

        :param path: url path
        :type path: str
        :param query_params: query string parameters
        :type query_params: dict
        :returns: constructed url
        :rtype: str
        """

        url = self._url_pattern.format(
            host=self._host,
            port=self._port,
            path=path)

        if query_params is not None:
            query_string = urlencode(query_params)
            url = (url + '?{}').format(query_string)

        return url

    def _response_to_error(self, response):
        """
        :param response: HTTP resonse object
        :type response: requests.Response
        :returns: the error embedded in the response JSON
        :rtype: Error
        """

        message = response.json().get('message')
        if message is None:
            errors = response.json().get('errors')
            if errors is None:
                logger.error(
                    'Marathon server did not return a message: %s',
                    response.json())
                return Error('Unknown error from Marathon')

            msg = '\n'.join(error['error'] for error in errors)
            return Error('Error(s): {}'.format(msg))

        return Error('Error: {}'.format(response.json()['message']))

    def get_app(self, app_id, version=None):
        """Returns a representation of the requested application version. If
        version is None the return the latest version.

        :param app_id: the ID of the application
        :type app_id: str
        :param version: application version as a ISO8601 datetime
        :type version: str
        :returns: the requested Marathon application
        :rtype: (dict, Error)
        """

        app_id = normalize_app_id(app_id)
        if version is None:
            url = self._create_url('v2/apps{}'.format(app_id))
        else:
            url = self._create_url(
                'v2/apps{}/versions/{}'.format(app_id, version))

        logger.info('Getting %r', url)
        response = requests.get(url)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            # Looks like Marathon return different JSON for versions
            if version is None:
                return (response.json()['app'], None)
            else:
                return (response.json(), None)
        else:
            return (None, self._response_to_error(response))

    def get_app_versions(self, app_id, max_count=None):
        """Asks Marathon for all the versions of the Application up to a
        maximum count.

        :param app_id: the ID of the application
        :type app_id: str
        :param max_count: the maximum number of version to fetch
        :type max_count: int
        :returns: a list of all the version of the application
        :rtype: (list of str, Error)
        """

        if max_count is not None and max_count <= 0:
            return (
                None,
                Error(
                    'Maximum count must be a positive number: {}'.format(
                        max_count))
            )

        app_id = normalize_app_id(app_id)

        url = self._create_url('v2/apps{}/versions'.format(app_id))

        logger.info('Getting %r', url)
        response = requests.get(url)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            if max_count is None:
                return (response.json()['versions'], None)
            else:
                return (response.json()['versions'][:max_count], None)
        else:
            return (None, self._response_to_error(response))

    def get_apps(self):
        """Get a list of known applications.

        :returns: list of known applications
        :rtype: (list of dict, Error)
        """

        url = self._create_url('v2/apps')

        logger.info('Getting %r', url)
        response = requests.get(url)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            apps = response.json()['apps']
            return (apps, None)
        else:
            return (None, self._response_to_error(response))

    def add_app(self, app_resource):
        """Add a new application.

        :param app_resource: application resource
        :type app_resource: dict, bytes or file
        :returns: the application description
        :rtype: (dict, Error)
        """

        url = self._create_url('v2/apps')

        # The file type exists only in Python 2, preventing type(...) is file.
        if hasattr(app_resource, 'read'):
            app_json = json.load(app_resource)
        else:
            app_json = app_resource

        logger.info('Posting %r to %r', app_json, url)
        response = requests.post(url, json=app_json)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            return (response.json(), None)
        else:
            return (None, self._response_to_error(response))

    def update_app(self, app_id, payload, force=None):
        """Update an application.

        :param app_id: the application id
        :type app_id: str
        :param payload: the json payload
        :type payload: dict
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: (str, Error)
        """

        app_id = normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}'.format(app_id), params)

        logger.info('Putting %r to %r', payload, url)
        response = requests.put(url, json=payload)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            return (response.json().get('deploymentId'), None)
        else:
            return (None, self._response_to_error(response))

    def scale_app(self, app_id, instances, force=None):
        """Scales an application to the requested number of instances.

        :param app_id: the ID of the application to scale
        :type app_id: str
        :param instances: the requested number of instances
        :type instances: int
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: (bool, Error)
        """

        app_id = normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}'.format(app_id), params)

        logger.info('Putting to %r', url)
        response = requests.put(url, json={'instances': int(instances)})
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            deployment = response.json()['deploymentId']
            return (deployment, None)
        else:
            return (None, self._response_to_error(response))

    def stop_app(self, app_id, force=None):
        """Scales an application to zero instances.

        :param app_id: the ID of the application to stop
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: the resulting deployment ID
        :rtype: (bool, Error)
        """

        return self.scale_app(app_id, 0, force)

    def remove_app(self, app_id, force=None):
        """Completely removes the requested application.

        :param app_id: the ID of the application to remove
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: Error if it failed to remove the app; None otherwise
        :rtype: Error
        """

        app_id = normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}'.format(app_id), params)

        logger.info('Deleting %r', url)
        response = requests.delete(url)
        logger.info('Got (%r)', response.status_code)

        if _success(response.status_code):
            return None
        else:
            return self._response_to_error(response)

    def restart_app(self, app_id, force=None):
        """Performs a rolling restart of all of the tasks.

        :param app_id: the id of the application to restart
        :type app_id: str
        :param force: whether to override running deployments
        :type force: bool
        :returns: the deployment id and version; Error otherwise
        :rtype: (dict, Error)
        """

        app_id = normalize_app_id(app_id)

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url('v2/apps{}/restart'.format(app_id), params)

        logger.info('Posting %r', url)
        response = requests.post(url)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            return (response.json(), None)
        else:
            return (None, self._response_to_error(response))

    def get_deployment(self, deployment_id):
        """Returns a deployment.

        :param deployemnt_id: the id of the application to restart
        :type deployemnt_id: str
        :returns: a deployment
        :rtype: (dict, Error)
        """

        url = self._create_url('v2/deployments')

        logger.info('Getting %r', url)
        response = requests.get(url)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            deployment = next(
                (deployment for deployment in response.json()
                 if deployment_id == deployment['id']),
                None)

            return (deployment, None)
        else:
            return (None, self._response_to_error(response))

    def get_deployments(self, app_id=None):
        """Returns a list of deployments, optionally limited to an app.

        :param app_id: the id of the application to restart
        :type app_id: str
        :returns: a list of deployments
        :rtype: list of dict
        """

        url = self._create_url('v2/deployments')

        logger.info('Getting %r', url)
        response = requests.get(url)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            if app_id is not None:
                app_id = normalize_app_id(app_id)
                deployments = [
                    deployment for deployment in response.json()
                    if app_id in deployment['affectedApps']
                ]
            else:
                deployments = response.json()

            return (deployments, None)
        else:
            return (None, self._response_to_error(response))

    def _cancel_deployment(self, deployment_id, force):
        """Cancels an application deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :param force: if set to `False`, stop the deployment and
                      create a new rollback deployment to reinstate the
                      previous configuration. If set to `True`, simply stop the
                      deployment.
        :type force: bool
        :returns: an error if unable to rollback the deployment; None otherwise
        :rtype: Error
        """

        if not force:
            params = None
        else:
            params = {'force': 'true'}

        url = self._create_url(
            'v2/deployments/{}'.format(deployment_id),
            params)

        logger.info('Deleting %r', url)
        response = requests.delete(url)
        logger.info('Got (%r): %r', response.status_code, response.text)

        if _success(response.status_code):
            return None
        else:
            return self._response_to_error(response)

    def rollback_deployment(self, deployment_id):
        """Rolls back an application deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :returns: an error if unable to rollback the deployment; None otherwise
        :rtype: Error
        """

        return self._cancel_deployment(deployment_id, False)

    def stop_deployment(self, deployment_id):
        """Stops an application deployment.

        :param deployment_id: the deployment id
        :type deployment_id: str
        :returns: an error if unable to stop the deployment; None otherwise
        :rtype: Error
        """

        return self._cancel_deployment(deployment_id, True)


class Error(errors.Error):
    """ Class for describing errors while talking to the Marathon server.

    :param message: Error message
    :type message: str
    """

    def __init__(self, message):
        self._message = message

    def error(self):
        """Return error message

        :returns: The error message
        :rtype: str
        """

        return self._message


def normalize_app_id(app_id):
    """Normalizes the application id.

    :param app_id: raw application ID
    :type app_id: str
    :returns: normalized application ID
    :rtype: str
    """

    return quote('/' + app_id.strip('/'))


def _success(status_code):
    """Returns true if the success status is between [200, 300).

    :param response_status: the http response status
    :type response_status: int
    :returns: True for success status; False otherwise
    :rtype: bool
    """

    return status_code >= 200 and status_code < 300
