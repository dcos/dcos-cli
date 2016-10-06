import getpass
import sys
import threading

import requests
from requests.auth import AuthBase, HTTPBasicAuth
from six.moves import urllib
from six.moves.urllib.parse import urlparse

from dcos import config, util
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException, DCOSBadRequest,
                         DCOSException, DCOSHTTPException)

logger = util.get_logger(__name__)
lock = threading.Lock()

DEFAULT_TIMEOUT = 5

# only accessed from _request_with_auth
AUTH_CREDS = {}  # (hostname, auth_scheme, realm) -> AuthBase()


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


def _request_with_auth(response,
                       method,
                       url,
                       is_success=_default_is_success,
                       timeout=None,
                       verify=None,
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
    :param verify: whether to verify SSL certs or path to cert(s)
    :type verify: bool | str
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: requests.Response
    """

    i = 0
    while i < 3 and response.status_code == 401:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        auth_scheme, realm = get_auth_scheme(response)
        creds = (hostname, auth_scheme, realm)

        with lock:
            if creds not in AUTH_CREDS:
                auth = _get_http_auth(response, parsed_url, auth_scheme)
            else:
                auth = AUTH_CREDS[creds]

        # try request again, with auth
        response = _request(method, url, is_success, timeout, auth,
                            verify, **kwargs)

        # only store credentials if they're valid
        with lock:
            if creds not in AUTH_CREDS and response.status_code == 200:
                AUTH_CREDS[creds] = auth
            # acs invalid token
            elif response.status_code == 401 and \
                    auth_scheme in ["acsjwt", "oauthjwt"]:

                if config.get_config_val("core.dcos_acs_token") is not None:
                    msg = ("Your core.dcos_acs_token is invalid. "
                           "Please run: `dcos auth login`")
                    raise DCOSException(msg)

        i += 1

    if response.status_code == 401:
        raise DCOSAuthenticationException(response)

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

    if 'headers' not in kwargs:
        kwargs['headers'] = {'Accept': 'application/json'}

    verify = _verify_ssl(verify)

    # Silence 'Unverified HTTPS request' and 'SecurityWarning' for bad certs
    if verify is not None:
        silence_requests_warnings()

    response = _request(method, url, is_success, timeout,
                        verify=verify, **kwargs)

    if response.status_code == 401:
        response = _request_with_auth(response, method, url, is_success,
                                      timeout, verify, **kwargs)

    if is_success(response.status_code):
        return response
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


def _get_auth_credentials(username, hostname):
    """Get username/password for auth

    :param username: username user for authentication
    :type username: str
    :param hostname: hostname for credentials
    :type hostname: str
    :returns: username, password
    :rtype: str, str
    """

    if username is None:
        sys.stdout.write("{}'s username: ".format(hostname))
        sys.stdout.flush()
        username = sys.stdin.readline().strip()

    password = getpass.getpass("{}@{}'s password: ".format(username, hostname))

    return username, password


def get_auth_scheme(response):
    """Return authentication scheme and realm requested by server for 'Basic'
       or 'acsjwt' (DC/OS acs auth) or 'oauthjwt' (DC/OS acs oauth) type

    :param response: requests.response
    :type response: requests.Response
    :returns: auth_scheme, realm
    :rtype: (str, str)
    """

    if 'www-authenticate' in response.headers:
        auths = response.headers['www-authenticate'].split(',')
        scheme = next((auth_type.rstrip().lower() for auth_type in auths
                       if auth_type.rstrip().lower().startswith("basic") or
                       auth_type.rstrip().lower().startswith("acsjwt") or
                       auth_type.rstrip().lower().startswith("oauthjwt")),
                      None)
        if scheme:
            scheme_info = scheme.split("=")
            auth_scheme = scheme_info[0].split(" ")[0].lower()
            realm = scheme_info[-1].strip(' \'\"').lower()
            return auth_scheme, realm
        else:
            return None, None
    else:
        return None, None


def _get_http_auth(response, url, auth_scheme):
    """Get authentication mechanism required by server

    :param response: requests.response
    :type response: requests.Response
    :param url: parsed request url
    :type url: str
    :param auth_scheme: str
    :type auth_scheme: str
    :returns: AuthBase
    :rtype: AuthBase
    """

    hostname = url.hostname
    username = url.username
    password = url.password

    if 'www-authenticate' in response.headers:
        if auth_scheme not in ['basic', 'acsjwt', 'oauthjwt']:
            msg = ("Server responded with an HTTP 'www-authenticate' field of "
                   "'{}', DC/OS only supports 'Basic'".format(
                       response.headers['www-authenticate']))
            raise DCOSException(msg)

        if auth_scheme == 'basic':
            # for basic auth if username + password was present,
            # we'd already be authed by python requests module
            username, password = _get_auth_credentials(username, hostname)
            return HTTPBasicAuth(username, password)
        # dcos auth (acs or oauth)
        else:
            return _get_dcos_auth(auth_scheme, username, password, hostname)
    else:
        msg = ("Invalid HTTP response: server returned an HTTP 401 response "
               "with no 'www-authenticate' field")
        raise DCOSException(msg)


def _get_dcos_oauth_creds(dcos_url):
    """Get token credential for dcos oath

    :param dcos_url: dcos cluster url
    :type dcos_url: str
    :returns: token from browser for oauth flow
    :rtype: dict
    """

    oauth_login = 'login?redirect_uri=urn:ietf:wg:oauth:2.0:oob'
    url = urllib.parse.urljoin(dcos_url, oauth_login)
    msg = "\n{}\n\n    {}\n\n{} ".format(
          "Please go to the following link in your browser:",
          url,
          "Enter OpenID Connect ID Token:")
    sys.stderr.write(msg)
    sys.stderr.flush()
    token = sys.stdin.readline().strip()
    return {"token": token}


def _get_dcos_acs_auth_creds(username, password, hostname):
    """Get credentials for dcos acs auth

    :param username: username user for authentication
    :type username: str
    :param password: password for authentication
    :type password: str
    :param hostname: hostname for credentials
    :type hostname: str
    :returns: username/password credentials
    :rtype: dict
    """

    if password is None:
        username, password = _get_auth_credentials(username, hostname)
    return {"uid": username, "password": password}


def _get_dcos_auth(auth_scheme, username, password, hostname):
    """Get authentication flow for dcos acs auth and dcos oauth

    :param auth_scheme: authentication_scheme
    :type auth_scheme: str
    :param username: username user for authentication
    :type username: str
    :param password: password for authentication
    :type password: str
    :param hostname: hostname for credentials
    :type hostname: str
    :returns: DCOSAcsAuth
    :rtype: AuthBase
    """

    toml_config = config.get_config()
    token = config.get_config_val("core.dcos_acs_token", toml_config)
    if token is None:
        dcos_url = config.get_config_val("core.dcos_url", toml_config)
        if auth_scheme == "acsjwt":
            creds = _get_dcos_acs_auth_creds(username, password, hostname)
        else:
            creds = _get_dcos_oauth_creds(dcos_url)

        verify = _verify_ssl()
        # Silence 'Unverified HTTPS request' and 'SecurityWarning' for bad cert
        if verify is not None:
            silence_requests_warnings()

        url = urllib.parse.urljoin(dcos_url, 'acs/api/v1/auth/login')
        # using private method here, so we don't retry on this request
        # error here will be bubbled up to _request_with_auth
        response = _request('post', url, json=creds, verify=verify)

        if response.status_code == 200:
            token = response.json()['token']
            config.set_val("core.dcos_acs_token", token)

    return DCOSAcsAuth(token)


class DCOSAcsAuth(AuthBase):
    """Invokes DCOS Authentication flow for given Request object."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = "token={}".format(self.token)
        return r
