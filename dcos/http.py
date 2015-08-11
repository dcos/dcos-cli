import getpass
import sys
import threading

import requests
from dcos import util
from dcos.errors import DCOSException, DCOSHTTPException
from requests.auth import HTTPBasicAuth

from six.moves.urllib.parse import urlparse

logger = util.get_logger(__name__)
lock = threading.Lock()

DEFAULT_TIMEOUT = 5

# only accessed from _request_with_auth
AUTH_CREDS = {}  # (hostname, realm) -> AuthBase()


def _default_is_success(status_code):
    """Returns true if the success status is between [200, 300).

    :param response_status: the http response status
    :type response_status: int
    :returns: True for success status; False otherwise
    :rtype: bool
    """

    return 200 <= status_code < 300


@util.duration
def _request(method,
             url,
             is_success=_default_is_success,
             timeout=DEFAULT_TIMEOUT,
             auth=None,
             **kwargs):
    """Sends an HTTP request.

    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param timeout: request timeout
    :type timeout: int
    :param auth: authentication
    :type auth: AuthBase
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: Response
    """

    logger.info(
        'Sending HTTP [%r] to [%r]: %r',
        method,
        url,
        kwargs.get('headers'))

    try:
        response = requests.request(
            method=method,
            url=url,
            timeout=timeout,
            auth=auth,
            **kwargs)
    except requests.exceptions.ConnectionError as e:
        logger.exception("HTTP Connection Error")
        raise DCOSException('URL [{0}] is unreachable: {1}'.format(
            e.request.url, e))
    except requests.exceptions.Timeout as e:
        logger.exception("HTTP Timeout")
        raise DCOSException('Request to URL [{0}] timed out.'.format(
            e.request.url))
    except requests.exceptions.RequestException as e:
        logger.exception("HTTP Exception")
        raise DCOSException('HTTP Exception: {}'.format(e))

    logger.info('Received HTTP response [%r]: %r',
                response.status_code,
                response.text)

    return response


def _request_with_auth(response,
                       method,
                       url,
                       is_success=_default_is_success,
                       timeout=None,
                       **kwargs):
    """Try request (3 times) with credentials if 401 returned from server

    :param response: requests.response
    :type response: requests.Response
    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param timeout: request timeout
    :type timeout: int
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: requests.Response
    """
    i = 0
    while i < 3 and response.status_code == 401:
        hostname = urlparse(response.url).hostname
        creds = (hostname, _get_realm(response))

        with lock:
            if creds not in AUTH_CREDS:
                auth = _get_http_auth_credentials(response)
            else:
                auth = AUTH_CREDS[creds]

        # try request again, with auth
        response = _request(method, url, is_success, timeout, auth, **kwargs)

        # only store credentials if they're valid
        with lock:
            if creds not in AUTH_CREDS and response.status_code == 200:
                AUTH_CREDS[creds] = auth

        i += 1

    if response.status_code == 401:
        raise DCOSException("Authentication failed")

    return response


def request(method,
            url,
            is_success=_default_is_success,
            timeout=None,
            **kwargs):
    """Sends an HTTP request. If the server responds with a 401, ask the
    user for their credentials, and try request again (up to 3 times).

    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param timeout: request timeout
    :type timeout: int
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: Response
    """

    if 'headers' not in kwargs:
        kwargs['headers'] = {'Accept': 'application/json'}

    response = _request(method, url, is_success, timeout, **kwargs)

    if response.status_code == 401:
        response = _request_with_auth(response, method, url, is_success,
                                      timeout, **kwargs)

    if is_success(response.status_code):
        return response
    else:
        raise DCOSHTTPException(response)


def head(url, **kwargs):
    """Sends a HEAD request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('head', url, **kwargs)


def get(url, **kwargs):
    """Sends a GET request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('get', url, **kwargs)


def post(url, data=None, json=None, **kwargs):
    """Sends a POST request.

    :param url: URL for the new Request object
    :type url: str
    :param data: Request body
    :type data: dict, bytes, or file-like object
    :param json: JSON request body
    :type data: dict
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('post', url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    """Sends a PUT request.

    :param url: URL for the new Request object
    :type url: str
    :param data: Request body
    :type data: dict, bytes, or file-like object
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('put', url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    """Sends a PATCH request.

    :param url: URL for the new Request object
    :type url: str
    :param data: Request body
    :type data: dict, bytes, or file-like object
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('patch', url, data=data, **kwargs)


def delete(url, **kwargs):
    """Sends a DELETE request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('delete', url, **kwargs)


def silence_requests_warnings():
    """Silence warnings from requests.packages.urllib3.  See DCOS-1007."""
    requests.packages.urllib3.disable_warnings()


def _get_basic_auth_credentials(username, hostname):
    """Get username/password for basic auth

    :param username: username user for authentication
    :type username: str
    :param hostname: hostname for credentials
    :type hostname: str
    :returns: HTTPBasicAuth
    :rtype: requests.auth.HTTPBasicAuth
    """

    if username is None:
        sys.stdout.write("{}'s username: ".format(hostname))
        sys.stdout.flush()
        username = sys.stdin.readline().strip().lower()

    password = getpass.getpass("{}@{}'s password: ".format(username, hostname))

    return HTTPBasicAuth(username, password)


def _get_realm(response):
    """Return authentication realm requested by server for 'Basic' type or None

    :param response: requests.response
    :type response: requests.Response
    :returns: realm
    :rtype: str | None
    """

    if 'www-authenticate' in response.headers:
        auths = response.headers['www-authenticate'].split(',')
        basic_realm = next((auth_type for auth_type in auths
                           if auth_type.rstrip().lower().startswith("basic")),
                           None)
        if basic_realm:
            realm = basic_realm.split('=')[-1].strip(' \'\"').lower()
            return realm
        else:
            return None
    else:
        return None


def _get_http_auth_credentials(response):
    """Get authentication credentials required by server

    :param response: requests.response
    :type response: requests.Response
    :returns: HTTPBasicAuth
    :rtype: HTTPBasicAuth
    """

    parsed_url = urlparse(response.url)
    hostname = parsed_url.hostname
    user = parsed_url.username

    if 'www-authenticate' in response.headers:
        realm = _get_realm(response)
        if realm:
            return _get_basic_auth_credentials(user, hostname)
        else:
            msg = ("Server responded with an HTTP 'www-authenticate' field of "
                   "'{}', DCOS only supports 'Basic'".format(
                       response.headers['www-authenticate']))
            raise DCOSException(msg)
    else:
        msg = ("Invalid HTTP response: server returned an HTTP 401 response "
               "with no 'www-authenticate' field")
        raise DCOSException(msg)
