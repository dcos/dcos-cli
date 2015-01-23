import requests

from . import errors


class Client(object):
    """Class for talking to the Marathon server. """

    def __init__(self, host, port):
        """Constructs interface for talking Marathon.

        :param host: Host for the Marathon server.
        :type host: str
        :param port: Port for the Marathon server.
        :type port: int
        """

        self._url_pattern = "http://{host}:{port}/{path}"
        self._host = host
        self._port = port

    def _create_url(self, path):
        """Creates the url from the provided path

        :param path: Url path
        :type path: str
        :return: Constructed url
        :rtype: str
        """

        return self._url_pattern.format(
            host=self._host,
            port=self._port,
            path=path)

    def start_app(self, app_resource):
        """Create and start a new application

        :param app_resource: Application resource
        :type app_resource: dict, bytes, or file
        :returns: Status of trying to start the application
        :rtype: (bool, Error)
        """

        url = self._create_url('v2/apps')
        response = requests.post(url, data=app_resource)

        if response.status_code == 201:
            return (True, None)
        else:
            return (
                None,
                Error(
                    'Error talking to Marathon: {}'.format(
                        response.json()['message'])))


class Error(errors.Error):
    def __init__(self, message):
        """Constructs error for Marathon calls

        :param message: Error message
        :type message: str
        """

        self._message = message

    def error(self):
        """Return error message

        :returns: The error message
        :rtype: str
        """

        return self._message
