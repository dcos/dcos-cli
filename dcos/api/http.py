import requests
from dcos.api import util
from dcos.api.errors import DefaultError

logger = util.get_logger(__name__)


def _default_is_success(status_code):
    """Returns true if the success status is between [200, 300).

    :param response_status: the http response status
    :type response_status: int
    :returns: True for success status; False otherwise
    :rtype: bool
    """

    return status_code >= 200 and status_code < 300


def _default_response_to_error(response):
    """
    :param response: HTTP resonse object
    :type response: requests.Response
    :returns: the error embedded in the response JSON
    :rtype: Error
    """

    return DefaultError('{}: {}'.format(response.status_code, response.text))


def request(method,
            url,
            is_success=_default_is_success,
            response_to_error=_default_response_to_error,
            **kwargs):
    """Sends an HTTP request.

    :param method: method for the new Request object
    :type method: str
    :param url: URL for the new Request object
    :type url: str
    :param is_success: Defines successful status codes for the request
    :type is_success: Function from int to bool
    :param response_to_error: Builds an Error from an unsuccessful response
    :type response_to_error: Function from requests.Response to Error
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
            response = session.send(request.prepare())

        logger.info('Received HTTP response [%r]: %r',
                    response.status_code,
                    response.text)

        if is_success(response.status_code):
            return (response, None)
        else:
            return (None, response_to_error(response))

    except Exception as ex:
        return (None, DefaultError(str(ex)))


def head(url, **kwargs):
    """Sends a HEAD request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    return request('head', url, **kwargs)


def get(url, **kwargs):
    """Sends a GET request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
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
    :rtype: (Response, Error)
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
    :rtype: (Response, Error)
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
    :rtype: (Response, Error)
    """

    return request('patch', url, data=data, **kwargs)


def delete(url, **kwargs):
    """Sends a DELETE request.

    :param url: URL for the new Request object
    :type url: str
    :param kwargs: Additional arguments to requests.request
                   (see py:func:`request`)
    :type kwargs: dict
    :rtype: (Response, Error)
    """

    return request('delete', url, **kwargs)
