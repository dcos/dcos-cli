import requests

from . import errors


class Client(object):
    """Class for talking to the Marathon server. """

    def __init__(self, host, port):
        """Constructs interface for talking Marathon.

        :param host: (string) Host for the Marathon server.
        :param port: (int) Port for the Marathon server.

        """
        self._url_pattern = "http://{host}:{port}/{path}"
        self._host = host
        self._port = port

    def _create_url(self, path):
        return self._url_pattern.format(
            host=self._host,
            port=self._port,
            path=path)

    def start_app(self, app_resource):
        """Create and start a new application

        :param app_resource: (dict) Application resource

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
        self._message = message

    def error(self):
        return self._message
