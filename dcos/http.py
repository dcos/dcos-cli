import requests

from requests.auth import AuthBase

from six.moves.urllib.parse import urlparse

from dcos import config, util
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException, DCOSBadRequest,
                         DCOSConnectionError, DCOSException, DCOSHTTPException,
                         DCOSUnprocessableException)


logger = util.get_logger(__name__)

DEFAULT_READ_TIMEOUT = 180
"""The default timeout for reading an HTTP response, it can be overriden
through the `core.timeout` config. This is not a time limit on the entire
response download; rather, an exception is raised if the server has not issued
a response for timeout seconds (more precisely, if no bytes have been received
on the underlying socket for timeout seconds)."""

DEFAULT_CONNECT_TIMEOUT = 5
"""The default timeout for establishing an HTTP connection."""

DEFAULT_TIMEOUT = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT)
"""The default timeout tuple for connection and read."""


def _default_is_success(status_code):
    """Returns true if the success status is between [200, 300).

    :param response_status: the http response status
    :type response_status: int
    :returns: True for success status; False otherwise
    :rtype: bool
    """

    return 200 <= status_code < 300


def _is_request_to_dcos(url, toml_config=None):
    """Checks if a request is for the DC/OS cluster.

    :param url: URL of the request
    :type url: str
    :param toml_config: cluster config to use
    :type toml_config: Toml
    :return: whether the request is for the cluster
    :rtype: bool
    """

    if toml_config is None:
        toml_config = config.get_config()

    dcos_url = urlparse(config.get_config_val("core.dcos_url", toml_config))
    cosmos_url = urlparse(
        config.get_config_val("package.cosmos_url", toml_config))
    parsed_url = urlparse(url)

    # request should match scheme + netloc
    def _request_match(expected_url, actual_url):
        return expected_url.scheme == actual_url.scheme and \
                    expected_url.netloc.lower() == actual_url.netloc.lower()

    is_request_to_cluster = _request_match(dcos_url, parsed_url) or \
        _request_match(cosmos_url, parsed_url)

    return is_request_to_cluster


def _verify_ssl(url, verify=None, toml_config=None):
    """Returns whether to verify ssl for the given url

    :param url: the target URL
    :type url: str
    :param verify: whether to verify SSL certs or path to cert(s)
    :type verify: bool | str
    :param toml_config: cluster config to use
    :type toml_config: Toml
    :return: whether to verify SSL certs or path to cert(s)
    :rtype: bool | str
    """

    if verify is None:
        if toml_config is None:
            toml_config = config.get_config()

        if not _is_request_to_dcos(url, toml_config):
            # Leave verify to None if URL is outside the DC/OS cluster
            # https://jira.mesosphere.com/browse/DCOS_OSS-618
            return None

        verify = config.get_config_val("core.ssl_verify", toml_config)
        if verify and verify.lower() == "true":
            verify = True
        elif verify and verify.lower() == "false":
            verify = False

    return verify


@util.duration
def _request(method,
             url,
             is_success=_default_is_success,
             timeout=True,
             auth=None,
             verify=None,
             toml_config=None,
             **kwargs):
    """Sends an HTTP request.

    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param timeout: How many seconds to wait for the server to send data
                    before aborting and raising an exception. A timeout is
                    either a float, a (connect timeout, read timeout) tuple
                    or `None`. `None` means unlimited timeout. If no timeout
                    is passed it defaults to the DEFAULT_TIMEOUT tuple, where
                    the connect timeout can optionally be overridden by the
                    `core.timeout` config.
    :type timeout: int | float | None | bool |
                   (int | float | None, int | float | None)
    :param auth: authentication
    :type auth: AuthBase
    :param verify: whether to verify SSL certs or path to cert(s)
    :type verify: bool | str
    :param toml_config: cluster config to use
    :type toml_config: Toml
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: Response
    """

    if timeout is True:
        if toml_config is None:
            toml_config = config.get_config()

        timeout = config.get_config_val("core.timeout", toml_config)
        timeout = (DEFAULT_CONNECT_TIMEOUT, timeout or DEFAULT_READ_TIMEOUT)
    elif type(timeout) in (float, int):
        timeout = (DEFAULT_CONNECT_TIMEOUT, timeout)

    if 'headers' not in kwargs:
        kwargs['headers'] = {'Accept': 'application/json'}

    verify = _verify_ssl(url, verify, toml_config)

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
        raise DCOSConnectionError(url)
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
            timeout=True,
            verify=None,
            toml_config=None,
            **kwargs):
    """Sends an HTTP request. If the server responds with a 401, ask the
    user for their credentials, and try request again (up to 3 times).

    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param timeout: How many seconds to wait for the server to send data
                    before aborting and raising an exception. A timeout is
                    either a float, a (connect timeout, read timeout) tuple
                    or `None`. `None` means unlimited timeout. If no timeout
                    is passed it defaults to the DEFAULT_TIMEOUT tuple, where
                    the connect timeout can optionally be overridden by the
                    `core.timeout` config.
    :type timeout: int | float | None | bool |
                   (int | float | None, int | float | None)
    :param verify: whether to verify SSL certs or path to cert(s)
    :type verify: bool | str
    :param toml_config: cluster config to use
    :type toml_config: Toml
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: Response
    """

    if toml_config is None:
        toml_config = config.get_config()

    auth_token = config.get_config_val("core.dcos_acs_token", toml_config)
    prompt_login = config.get_config_val("core.prompt_login", toml_config)
    dcos_url = urlparse(config.get_config_val("core.dcos_url", toml_config))

    # only request with DC/OS Auth if request is to DC/OS cluster
    if auth_token and _is_request_to_dcos(url, toml_config=toml_config):
        auth = DCOSAcsAuth(auth_token)
    else:
        auth = None

    response = _request(method, url, is_success, timeout,
                        auth=auth, verify=verify, toml_config=toml_config,
                        **kwargs)

    if is_success(response.status_code):
        return response
    elif response.status_code == 401:
        if prompt_login:
            # I don't like having imports that aren't at the top level, but
            # this is to resolve a circular import issue between dcos.http and
            # dcos.auth
            from dcos.auth import header_challenge_auth

            header_challenge_auth(dcos_url.geturl())
            # if header_challenge_auth succeeded, then we auth-ed correctly and
            # thus can safely recursively call ourselves and not have to worry
            # about an infinite loop
            return request(method=method, url=url,
                           is_success=is_success, timeout=timeout,
                           verify=verify, **kwargs)
        else:
            if auth_token is not None:
                msg = ("Your core.dcos_acs_token is invalid. "
                       "Please run: `dcos auth login`")
                raise DCOSAuthenticationException(response, msg)
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
