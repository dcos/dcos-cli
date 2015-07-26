import requests
from dcos import util
from dcos.errors import DCOSException

logger = util.get_logger(__name__)

DEFAULT_TIMEOUT = 5


def _timeout():
    config = util.get_config()
    return config.get('core.timeout', DEFAULT_TIMEOUT)


def _default_is_success(status_code):
    """Returns true if the success status is between [200, 300).

    :param response_status: the http response status
    :type response_status: int
    :returns: True for success status; False otherwise
    :rtype: bool
    """

    return status_code >= 200 and status_code < 300


def _default_to_exception(response):
    """
    :param response: HTTP response object or Exception
    :type response: requests.Response | Exception
    :returns: exception
    :rtype: Exception
    """

    if isinstance(response, Exception) and \
       not isinstance(response, requests.exceptions.RequestException):
        return response

    if isinstance(response, requests.exceptions.ConnectionError):
        return DCOSException('URL [{0}] is unreachable: {1}'
                             .format(response.request.url, response))
    elif isinstance(response, requests.exceptions.Timeout):
        return DCOSException(
            'Request to URL [{0}] timed out'.format(response.request.url))
    elif isinstance(response, requests.exceptions.RequestException):
        return response
    else:
        return DCOSException(
            'Error while fetching [{0}]: HTTP {1}: {2}'.format(
                response.request.url, response.status_code, response.reason))


@util.duration
def request(method,
            url,
            is_success=_default_is_success,
            to_exception=_default_to_exception,
            timeout=None,
            **kwargs):
    """Sends an HTTP request.

    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param to_exception: Builds an Error from an unsuccessful response or Error
    :type to_exception: (requests.Response | Error) -> Error
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: Response
    """

    if 'headers' not in kwargs:
        kwargs['headers'] = {'Accept': 'application/json'}

    timeout = timeout or _timeout()

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
            **kwargs)
    except Exception as ex:
        logger.exception('Error making HTTP request: %r', url)

        raise to_exception(ex)

    logger.info('Received HTTP response [%r]: %r',
                response.status_code,
                response.text)

    if is_success(response.status_code):
        return response
    else:
        raise to_exception(response)


def head(url, to_exception=_default_to_exception, **kwargs):
    """Sends a HEAD request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('head', url, **kwargs)


def get(url, to_exception=_default_to_exception, **kwargs):
    """Sends a GET request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('get', url, to_exception=to_exception, **kwargs)


def post(url, to_exception=_default_to_exception,
         data=None, json=None, **kwargs):
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

    return request('post', url,
                   to_exception=to_exception, data=data, json=json, **kwargs)


def put(url, to_exception=_default_to_exception, data=None, **kwargs):
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

    return request('put', url, to_exception=to_exception, data=data, **kwargs)


def patch(url, to_exception=_default_to_exception, data=None, **kwargs):
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

    return request('patch', url,
                   to_exception=to_exception, data=data, **kwargs)


def delete(url, to_exception=_default_to_exception, **kwargs):
    """Sends a DELETE request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: Response
    """

    return request('delete', url, to_exception=to_exception, **kwargs)


def silence_requests_warnings():
    """Silence warnings from requests.packages.urllib3.  See DCOS-1007."""
    requests.packages.urllib3.disable_warnings()
