import requests
from requests.auth import AuthBase

from six.moves.urllib.parse import urlparse

from dcos import config, util
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException, DCOSBadRequest,
                         DCOSException, DCOSHTTPException,
                         DCOSUnprocessableException)


logger = util.get_logger(__name__)

DEFAULT_TIMEOUT = 5


def _default_is_success(status_code):
    """Returns true if the success status is between [200, 300).

    :param response_status: the http response status
    :type response_status: int
    :returns: True for success status; False otherwise
    :rtype: bool
    """

    return 200 <= status_code < 300


def _verify_ssl(verify=None):
    """Returns whether to verify ssl

    :param verify: whether to verify SSL certs or path to cert(s)
    :type verify: bool | str
    :return: whether to verify SSL certs or path to cert(s)
    :rtype: bool | str
    """

    if verify is None:
        verify = config.get_config_val("core.ssl_verify")
        if verify and verify.lower() == "true":
            verify = True
        elif verify and verify.lower() == "false":
            verify = False

    return verify


@util.duration
def _request(method,
             url,
             is_success=_default_is_success,
             timeout=DEFAULT_TIMEOUT,
             auth=None,
             verify=None,
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
    :param verify: whether to verify SSL certs or path to cert(s)
    :type verify: bool | str
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: Response
    """

    if 'headers' not in kwargs:
        kwargs['headers'] = {'Accept': 'application/json'}

    verify = _verify_ssl(verify)

    # Silence 'Unverified HTTPS request' and 'SecurityWarning' for bad certs
    if verify is not None:
        silence_requests_warnings()

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
            verify=verify,
            **kwargs)
    except requests.exceptions.SSLError as e:
        logger.exception("HTTP SSL Error")
        msg = ("An SSL error occurred. To configure your SSL settings, "
               "please run: `dcos config set core.ssl_verify <value>`")
        description = config.get_property_description("core", "ssl_verify")
        if description is not None:
            msg += "\n<value>: {}".format(description)
        raise DCOSException(msg)
    except requests.exceptions.ConnectionError as e:
        logger.exception("HTTP Connection Error")
        raise DCOSException('URL [{0}] is unreachable: {1}'.format(url, e))
    except requests.exceptions.Timeout as e:
        logger.exception("HTTP Timeout")
        raise DCOSException('Request to URL [{0}] timed out.'.format(url))
    except requests.exceptions.RequestException as e:
        logger.exception("HTTP Exception")
        raise DCOSException('HTTP Exception: {}'.format(e))

    logger.info('Received HTTP response [%r]: %r',
                response.status_code,
                response.headers)

    return response


def request(method,
            url,
            is_success=_default_is_success,
            timeout=None,
            verify=None,
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
    :param verify: whether to verify SSL certs or path to cert(s)
    :type verify: bool | str
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: Response
    """

    toml_config = config.get_config()
    auth_token = config.get_config_val("core.dcos_acs_token", toml_config)
    dcos_url = urlparse(config.get_config_val("core.dcos_url", toml_config))
    parsed_url = urlparse(url)

    # only request with DC/OS Auth if request is to DC/OS cluster
    # request should match scheme + netloc
    scheme_eq = parsed_url.scheme == dcos_url.scheme
    netloc_eq = parsed_url.netloc == dcos_url.netloc
    if auth_token and scheme_eq and netloc_eq:
        auth = DCOSAcsAuth(auth_token)
    else:
        auth = None
    response = _request(method, url, is_success, timeout,
                        auth=auth, verify=verify, **kwargs)

    if is_success(response.status_code):
        return response
    elif response.status_code == 401:
        if auth_token is not None:
            msg = ("Your core.dcos_acs_token is invalid. "
                   "Please run: `dcos auth login`")
            raise DCOSAuthenticationException(msg)
        else:
            raise DCOSAuthenticationException(response)
    elif response.status_code == 422:
        raise DCOSUnprocessableException(response)
    elif response.status_code == 403:
        raise DCOSAuthorizationException(response)
    elif response.status_code == 400:
        raise DCOSBadRequest(response)
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


class DCOSAcsAuth(AuthBase):
    """Invokes DCOS Authentication flow for given Request object."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = "token={}".format(self.token)
        return r
