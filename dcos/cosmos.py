from six.moves import urllib

from dcos import config, http, util
from dcos.errors import DCOSBadRequest, DCOSException

logger = util.get_logger(__name__)


class Cosmos:
    """A wrapper on cosmos that abstracts away http requests"""

    def __init__(self, cosmos_url=None):
        if cosmos_url is None:
            self.cosmos_url = get_cosmos_url()
        else:
            self.cosmos_url = cosmos_url

        self._http_method = {
            'capabilities': 'get',
            'package/add': 'post',
            'package/describe': 'post',
            'package/install': 'post',
            'package/list': 'post',
            'package/list-versions': 'post',
            'package/render': 'post',
            'package/repository/add': 'post',
            'package/repository/delete': 'post',
            'package/repository/list': 'post',
            'package/search': 'post',
            'package/uninstall': 'post'
        }

        self._request_versions = {
            'capabilities': ['v1'],
            'package/add': ['v1'],
            'package/describe': ['v2', 'v1'],
            'package/install': ['v2', 'v1'],
            'package/list': ['v1'],
            'package/list-versions': ['v1'],
            'package/render': ['v1'],
            'package/repository/add': ['v1'],
            'package/repository/delete': ['v1'],
            'package/repository/list': ['v1'],
            'package/search': ['v1'],
            'package/uninstall': ['v1']
        }

        self._special_content_types = {
            ('package/add', 'v1'):
                'application/vnd.dcos.universe.package+zip;version=v1',
            ('capabilities', 'v1'):
                format_cosmos_header_type('capabilities', 'v1', '')
        }

        self._special_accepts = {
            ('capabilities', 'v1'):
                format_cosmos_header_type('capabilities', 'v1', '')
        }

    def call_cosmos_endpoint(self,
                             endpoint,
                             headers=None,
                             data=None,
                             json=None,
                             **kwargs):
        """
        Gets the Response object returned by comos at endpoint

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :param headers: these header values will appear
        in the request headers.
        :type headers: None | dict[str, str]
        :param data: the request's body
        :type data: dict | bytes | file-like object
        :param json: JSON request body
        :type json: dict
        :param kwargs: Additional arguments to requests.request
                       (see py:func:`request`)
        :type kwargs: dict
        :return: the Response object returned by cosmos
        :rtype: requests.Response
        """
        url = self._get_endpoint_url(endpoint)
        request_versions = self._get_request_version_preferences(endpoint)
        headers_preference = list(map(
            lambda version: self._get_header(
                endpoint, version, headers),
            request_versions))
        http_request_type = self._get_http_method(endpoint)
        return self._call_cosmos(
            url,
            http_request_type,
            headers_preference,
            data,
            remove_nones(json),
            **kwargs)

    def _call_cosmos(self,
                     url,
                     http_request_type,
                     headers_preference,
                     data=None,
                     json=None,
                     **kwargs):
        """
        Gets a Response object obtained by calling cosmos
        at the url 'url'. Will attempt each of the headers
        in headers_preference in order until success.

        :param url: the url of a cosmos endpoint
        :type url: str
        :param headers_preference: a list of request headers
        in order of preference. Each header
        will be attempted until they all fail or the request succeeds.
        :type headers_preference: list[dict[str, str]]
        :param data: the request's body
        :type data: dict | bytes | file-like object
        :param json: JSON request body
        :type json: dict
        :param kwargs: Additional arguments to requests.request
                       (see py:func:`request`)
        :type kwargs: dict
        :return: response returned by calling cosmos at url
        :rtype: requests.Response
        """
        try:
            headers = headers_preference[0]
            if http_request_type is 'post':
                response = http.post(
                    url, data=data, json=json, headers=headers, **kwargs)
            else:
                response = http.get(
                    url, data=data, json=json, headers=headers, **kwargs)
            if not _matches_expected_response_header(headers,
                                                     response.headers):
                raise DCOSException(
                    'Server returned incorrect response type, '
                    'expected {} but got {}'.format(
                        headers.get('Accept'),
                        response.headers.get('Content-Type')))
        except DCOSBadRequest as e:
            if len(headers_preference) > 1:
                # reattempt with one less item in headers_preference
                response = self._call_cosmos(url,
                                             http_request_type,
                                             headers_preference[1:],
                                             data,
                                             json,
                                             **kwargs)
            else:
                raise e
        return response

    def _get_endpoint_url(self, endpoint):
        """
        Gets the url for the cosmos endpoint 'endpoint'

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :return: the url of endpoint
        :rtype: str
        """
        return urllib.parse.urljoin(self.cosmos_url, endpoint)

    def _get_request_version_preferences(self, endpoint):
        """
        Gets the list of versions for endpoint in preference order.
        The first item is most preferred, and last is least preferred.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :return: list of versions in preference order
        :rtype: list[str]
        """
        return self._request_versions.get(endpoint)

    def _get_http_method(self, endpoint):
        """
        Gets the http method cosmos expects for the endpoint
        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :return: http method type
        :rtype: str
        """
        method = self._http_method.get(endpoint)

        if method is not 'post' and method is not 'get':
            raise DCOSException('Bad method type')

        return method

    def _get_header(self, endpoint, version, headers=None):
        """
        Given an cosmos endpoint, a version, and any extra header values,
        gets the header that can be used to query cosmos at endpoint.
        Any key in headers will appear in the final header. In effect the
        user function can overwrite the default header.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :param version: The version of the request
        :type version: str
        :param headers: extra keys for the header
        :type headers: dict[str, str]
        :return: a header that can be used to query cosmos at endpoint
        :rtype: dict[str, str]
        """
        simple_header = {
            'Content-Type': self._get_content_type(endpoint),
            'Accept': self._get_accept(endpoint, version)
        }
        return remove_nones(merge_dict(simple_header, headers))

    def _get_accept(self, endpoint, version):
        """
        Gets the value for the Accept header key for
        the cosmos request at endpoint.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :param version: The version of the request
        :type version: str
        :return: the value for the Accept header key for endpoint
        :rtype: str
        """
        if (endpoint, version) in self._special_accepts:
            return self._special_accepts[(endpoint, version)]
        return format_cosmos_header_type(endpoint, version, 'response')

    def _get_content_type(self, endpoint):
        """
        Gets the value for the Content-Type header key for
        the cosmos request at endpoint.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :return: the value for the Content-Type header key for endpoint
        :rtype: str
        """
        version = 'v1'
        if (endpoint, version) in self._special_content_types:
            return self._special_content_types[(endpoint, version)]
        return format_cosmos_header_type(endpoint, version, 'request')


def format_cosmos_header_type(endpoint, version, suffix):
    """
    Formats a value for a cosmos Content-Type or Accept header key.

    :param endpoint: a cosmos endpoint, of the form 'x/y',
    for example 'package/repo/add', 'service/start', or 'package/error'
    :type endpoint: str
    :param version: The version of the request
    :type version: str
    :param suffix: The string that will be appended to
    endpoint type, most commonly 'request' or 'response'
    :type suffix: str
    :return: a formatted value for a Content-Type or Accept header key
    :rtype: str
    """
    prefix = endpoint.replace('/', '.')
    separator = '-'
    if suffix is None or suffix is "":
        separator = ''
    return ('application/vnd.dcos.{}{}{}'
            '+json;charset=utf-8;version={}').format(prefix,
                                                     separator,
                                                     suffix,
                                                     version)


def _matches_expected_response_header(request_headers, response_headers):
    """
    Returns true if the Content-Type value of the response header matches the
    Accept value of the request header, false otherwise

    :param request_headers: the headers for a cosmos request
    :type request_headers: dict[str, str]
    :param response_headers: the headers for a cosmos response
    :type response_headers: dict[str, str]
    :return: true if the Content-Type value of the response header matches the
    Accept value of the request header, false otherwise
    :rtype: bool
    """
    return (request_headers.get('Accept')
            in response_headers.get('Content-Type'))


def get_cosmos_url():
    """
    Gets the cosmos url

    :returns: cosmos base url
    :rtype: str
    """
    toml_config = config.get_config()
    cosmos_url = config.get_config_val('package.cosmos_url', toml_config)
    if cosmos_url is None:
        cosmos_url = config.get_config_val('core.dcos_url', toml_config)
        if cosmos_url is None:
            raise config.missing_config_exception(['core.dcos_url'])
    return cosmos_url


def remove_nones(dictionary):
    """
    Given a dictionary, create a shallow copy of dictionary where
    any key whose corresponding value is none is removed.

    :param dictionary: a dictionary
    :type dictionary: dict
    :return: a shallow copy of dictionary in which all keys whose value
    is none have been removed
    :rtype: dict
    """
    return dict(filter(lambda kv: kv[1] is not None, dictionary.items()))


def merge_dict(a, b):
    """
    Given two dicts, merge them into a new dict as a
    shallow copy. Keys on dictionary b will overwrite keys
    on dictionary a.

    :param a: a dictionary, may be None
    :type a: None | dict
    :param b: a dictionary, may be None
    :type b: None | dict
    :return: the result of merging a with b
    :rtype: dict
    """
    if a is None and b is None:
        return {}

    if a is None:
        return b

    if b is None:
        return a

    z = a.copy()
    z.update(b)
    return z
