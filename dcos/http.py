import requests
from dcos import util
from dcos.errors import DefaultError, Error

logger = util.get_logger(__name__)


def _default_is_success(status_code):
    """Returns true if the success status is between [200, 300).

    :param response_status: the http response status
    :type response_status: int
    :returns: True for success status; False otherwise
    :rtype: bool
    """

    return status_code >= 200 and status_code < 300


def _default_to_error(response):
    """
    :param response: HTTP response object or Error
    :type response: requests.Response or Error
    :returns: the error embedded in the response JSON
    :rtype: Error
    """

    if isinstance(response, Error):
        return response

    return DefaultError('{}: {}'.format(response.status_code, response.text))


def request(method,
            url,
            is_success=_default_is_success,
            to_error=_default_to_error,
            **kwargs):
    """Sends an HTTP request.

    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param to_error: Builds an Error from an unsuccessful response or Error
    :type to_error: Function from requests.Response or Error to Error
    :param kwargs: Additional arguments to requests.request
        (see http://docs.python-requests.org/en/latest/api/#requests.request)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    try:
        if 'headers' in kwargs:
            request = requests.Request(method=method, url=url, **kwargs)
        else:
            request = requests.Request(
                method=method,
                url=url,
                headers={'Accept': 'application/json'},
                **kwargs)

        logger.info(
            'Sending HTTP [%r] to [%r]: %r',
            request.method,
            request.url,
            request.headers)

        with requests.Session() as session:
            response = session.send(request.prepare(), timeout=3.0)

        logger.info('Received HTTP response [%r]: %r',
                    response.status_code,
                    response.text)

        if is_success(response.status_code):
            return (response, None)
        else:
            return (None, to_error(response))

    except Exception as ex:
        return (None, to_error(DefaultError(str(ex))))


def head(url, to_error=_default_to_error, **kwargs):
    """Sends a HEAD request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    return request('head', url, **kwargs)


def get(url, to_error=_default_to_error, **kwargs):
    """Sends a GET request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    return request('get', url, to_error=to_error, **kwargs)


def post(url, to_error=_default_to_error, data=None, json=None, **kwargs):
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
    :rtype: (Response, Error)
    """

    return request('post',
                   url, to_error=to_error, data=data, json=json, **kwargs)


def put(url, to_error=_default_to_error, data=None, **kwargs):
    """Sends a PUT request.

    :param url: URL for the new Request object
    :type url: str
    :param data: Request body
    :type data: dict, bytes, or file-like object
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    return request('put', url, to_error=to_error, data=data, **kwargs)


def patch(url, to_error=_default_to_error, data=None, **kwargs):
    """Sends a PATCH request.

    :param url: URL for the new Request object
    :type url: str
    :param data: Request body
    :type data: dict, bytes, or file-like object
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    return request('patch', url, to_error=to_error, data=data, **kwargs)


def delete(url, to_error=_default_to_error, **kwargs):
    """Sends a DELETE request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    return request('delete', url, to_error=to_error, **kwargs)


def silence_requests_warnings():
    """Silence warnings from requests.packages.urllib3.  See DCOS-1007."""
    requests.packages.urllib3.disable_warnings()
