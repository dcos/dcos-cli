import collections
import functools

import six
from six.moves import urllib

from dcos import config, http, util
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException, DCOSBadRequest,
                         DCOSException, DCOSHTTPException)

logger = util.get_logger(__name__)


def cosmos_error(fn):
    """Decorator for errors returned from cosmos

    :param fn: function to check for errors from cosmos
    :type fn: function
    :rtype: Response
    :returns: Response
    """

    @functools.wraps(fn)
    def check_for_cosmos_error(*args, **kwargs):
        """Returns response from cosmos or raises exception

        :returns: Response or raises Exception
        :rtype: valid response
        """
        response = fn(*args, **kwargs)
        content_type = response.headers.get('Content-Type')
        if content_type is None:
            raise DCOSHTTPException(response)
        elif _format_header_type('package/error', 'v1', '') in content_type:
            logger.debug('Error: {}'.format(response.json()))
            error_msg = _format_error_message(response.json())
            raise DCOSException(error_msg)
        return response

    return check_for_cosmos_error


class Cosmos:
    """A wrapper on cosmos service, abstracts away http request,
    endpoint headers, and versions"""

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

        self._versions = {
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
            ('capabilities', 'v1'):
                _format_header_type('capabilities', 'v1', '')
        }

        self._special_accepts = {
            ('capabilities', 'v1'):
                _format_header_type('capabilities', 'v1', '')
        }

    def capabilities(self):
        """
        Calls cosmos' capabilities endpoint.

        :return: Response returned by cosmos' capabilities endpoint
        :rtype: Response
        """
        endpoint = 'capabilities'
        return self._call_cosmos_endpoint(endpoint)

    def package_add(self, dcos_package):
        """
        Calls cosmos' package/add endpoint.

        :param dcos_package: path to the DC/OS package
        :type dcos_package: str
        :return: Response returned by cosmos' package/add endpoint
        :rtype: Response
        """
        endpoint = 'package/add'
        with util.open_file(dcos_package, 'rb') as pkg:
            extra_headers = {'Content-MD5': util.md5_hash_file(pkg)}
        with util.open_file(dcos_package, 'rb') as data:
            return self._call_cosmos_endpoint(
                endpoint, extra_headers, data=data)

    def package_describe(self, package_name, package_version=None):
        """
        Calls cosmos' package/describe endpoint.

        :param package_name: the name of the universe package to describe
        :type package_name: str
        :param package_version:  the version of the universe package
        :type package_version: None | str
        :return: Response returned by cosmos' package/describe endpoint
        :rtype: Response
        """
        endpoint = 'package/describe'
        json = remove_nones({
            'packageName': package_name,
            'packageVersion': package_version
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_install(self,
                        package_name,
                        package_version=None,
                        options=None,
                        app_id=None):
        """
        Calls cosmos' package/install endpoint.

        :param package_name: the name of the universe package to install
        :type package_name: str
        :param package_version:  the version of the universe package
        :type package_version: None | str
        :param options: the options for the universe package
        :type options: None | dict
        :param app_id: the app id of the universe package
        :type app_id: None | str
        :return: Response returned by cosmos' package/install endpoint
        :rtype: Response
        """
        endpoint = 'package/install'
        json = remove_nones({
            'packageName': package_name,
            'packageVersion': package_version,
            'options': options,
            'appId': app_id
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_list(self, package_name=None, app_id=None):
        """
        Calls cosmos' package/list endpoint.

        :param package_name: the name of the package
        :type package_name: None | str
        :param app_id: the app id of the package
        :type app_id: None | str
        :return: Response returned by cosmos' package/list endpoint
        :rtype: Response
        """
        endpoint = 'package/list'
        json = remove_nones({
            'packageName': package_name,
            'appId': app_id
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_list_versions(self,
                              package_name,
                              include_package_versions=True):
        """
        Calls cosmos' package/list-versions endpoint.

        :param package_name: the name of the package
        :type package_name: str
        :param include_package_versions: ???
        :type include_package_versions: bool
        :return: Response returned by cosmos' package/list-versions endpoint
        :rtype: Response
        """
        endpoint = 'package/list-versions'
        json = remove_nones({
            'packageName': package_name,
            'includePackageVersions': include_package_versions
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_render(self,
                       package_name,
                       package_version=None,
                       options=None,
                       app_id=None):
        """
        Calls cosmos' package/render endpoint.

        :param package_name: the name of the universe package to render
        :type package_name: str
        :param package_version:  the version of the universe package
        :type package_version: None | str
        :param options: the options for the universe package
        :type options: None | dict
        :param app_id: the app id of the universe package
        :type app_id: None | str
        :return: Response returned by cosmos' package/render endpoint
        :rtype: Response
        """
        endpoint = 'package/render'
        json = remove_nones({
            'packageName': package_name,
            'packageVersion': package_version,
            'options': options,
            'appId': app_id
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_repository_add(self, name, uri, index=None):
        """
        Calls cosmos' package/repository/add endpoint.

        :param name: the name to be assigned to the repository
        :type name: str
        :param uri: the uri of the repository
        :type uri: str
        :param index: the priority of this repository
        :type index: None | int
        :return: Response returned by cosmos' package/repository/add endpoint
        :rtype: Response
        """
        endpoint = 'package/repository/add'
        json = remove_nones({
            'name': name,
            'uri': uri,
            'index': index
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_repository_delete(self, name=None, uri=None):
        """
        Calls cosmos' package/repository/delete endpoint.

        :param name: the name of the repository
        :type name: None | str
        :param uri: the uri of the repository
        :type uri: None | str
        :return: Response returned by cosmos'
        package/repository/delete endpoint
        :rtype: Response
        """
        endpoint = 'package/repository/delete'
        json = remove_nones({
            'name': name,
            'uri': uri
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_repository_list(self):
        """
        Calls cosmos' package/repository/list endpoint.

        :return: Response returned by cosmos' package/repository/list endpoint
        :rtype: Response
        """
        endpoint = 'package/repository/list'
        return self._call_cosmos_endpoint(endpoint, json={})

    def package_search(self, query=None):
        """
        Calls cosmos' package/search endpoint.

        :param query: a query on the packages
        :type query: None | str
        :return: Response returned by cosmos' package/search endpoint
        :rtype: Response
        """
        endpoint = 'package/search'
        json = remove_nones({
            'query': query
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    def package_uninstall(self, package_name, app_id=None, all=None):
        """
        Calls cosmos' package/uninstall endpoint.

        :param package_name: the name of the package
        :type package_name: str
        :param app_id: the app id of the package
        :type app_id: None | str
        :param all: if to uninstall all packages that
        match the package name and app id
        :param all: None | bool
        :return: Response returned by cosmos' package/uninstall endpoint
        :rtype: Response
        """
        endpoint = 'package/uninstall'
        json = remove_nones({
            'packageName': package_name,
            'appId': app_id,
            'all': all
        })
        return self._call_cosmos_endpoint(endpoint, json=json)

    @cosmos_error
    def _call_cosmos_endpoint(self,
                              endpoint,
                              extra_headers=None,
                              data=None,
                              json=None,
                              **kwargs):
        """
        Gets a Response object obtained by calling
         the cosmos endpoint 'endpoint'.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :param extra_headers: extra keys for the header,
        these header values will appear
        in the request headers.
        :type extra_headers: None | dict[str, str]
        :param data: the request's body
        :type data: dict | bytes | file-like object
        :param json: JSON request body
        :type json: dict
        :param kwargs: Additional arguments to requests.request
                       (see py:func:`request`)
        :type kwargs: dict
        :return: response returned by calling cosmos at endpoint
        :rtype: Response
        """
        url = self._get_endpoint_url(endpoint)
        versions = self._get_version_preferences(endpoint)
        headers_preference = list(map(
            lambda version: self._get_header(
                endpoint, version, extra_headers),
            versions))
        method = self._get_http_method(endpoint)

        if method is 'post':
            return self._call_cosmos(
                url, http.post, headers_preference, data, json, **kwargs)
        elif method is 'get':
            return self._call_cosmos(
                url, http.get, headers_preference, data, json, **kwargs)
        else:
            raise DCOSException('bad request type')

    def _call_cosmos(self,
                     url,
                     http_method_fn,
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
        :param http_method_fn:
        :type http_method_fn:
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
        :rtype: Response
        """
        try:
            headers = headers_preference[0]
            response = http_method_fn(
                url, data=data, json=json, headers=headers, **kwargs)
            if not _matches_expected_response_header(headers,
                                                     response.headers):
                raise DCOSException(
                    'Server returned incorrect response type, '
                    'expected {} but got {}'.format(
                        headers.get('Accept'),
                        response.headers.get('Content-Type')))
        except DCOSAuthenticationException:
            raise
        except DCOSAuthorizationException:
            raise
        except DCOSBadRequest as e:
            if len(headers_preference) > 1:
                # recurse with one less item in headers_preference
                response = self._call_cosmos(url,
                                             http_method_fn,
                                             headers_preference[1:],
                                             data,
                                             json,
                                             **kwargs)
            else:
                response = e.response
        except DCOSHTTPException as e:
            # let non authentication responses be handled by `cosmos_error` so
            # we can expose errors reported by cosmos
            response = e.response
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

    def _get_version_preferences(self, endpoint):
        """
        Gets the list of versions for endpoint in preference order.
        The first item is most preferred, and last is least preferred.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :return: list of versions in preference order
        :rtype: list[str]
        """
        return self._versions.get(endpoint)

    def _get_http_method(self, endpoint):
        """
        Gets the http method cosmos expects for the endpoint

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :return: http method type
        :rtype: str
        """
        return self._http_method.get(endpoint)

    def _get_header(self, endpoint, version, extra_headers=None):
        """
        Given an cosmos endpoint, a version, and any extra header values,
        gets the header that can be used to query cosmos at endpoint.
        Any key in extra_headers will appear in the final header.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :param version: The version of the request
        :type version: str
        :param extra_headers: extra keys for the header
        :type extra_headers: dict[str, str]
        :return: a header that can be used to query cosmos at endpoint
        :rtype: dict[str, str]
        """
        simple_header = {
            'Content-Type': self._get_content_type(endpoint, version),
            'Accept': self._get_accept(endpoint, version)
        }
        return merge_dict(simple_header, extra_headers)

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
        return _format_header_type(endpoint, version, 'response')

    def _get_content_type(self, endpoint, version):
        """
        Gets the value for the Content-Type header key for
        the cosmos request at endpoint.

        :param endpoint: a cosmos endpoint, of the form 'x/y',
        for example 'package/repo/add' or 'service/start'
        :type endpoint: str
        :param version: The version of the request
        :type version: str
        :return: the value for the Content-Type header key for endpoint
        :rtype: str
        """
        if (endpoint, version) in self._special_content_types:
            return self._special_content_types[(endpoint, version)]
        return _format_header_type(endpoint, version, 'request')


def _format_header_type(endpoint, version, suffix):
    """
    Formats a value for a cosmos Content-Type or Accept header key.

    :param endpoint: a cosmos endpoint, of the form 'x/y',
    for example 'package/repo/add' or 'service/start'
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


def _format_error_message(error):
    """Returns formatted error message based on error type

    :param error: cosmos error
    :type error: dict
    :returns: formatted error
    :rtype: str
    """
    if error.get("type") == "AmbiguousAppId":
        helper = (".\nPlease use --app-id to specify the ID of the app "
                  "to uninstall, or use --all to uninstall all apps.")
        error_message = error.get("message") + helper
    elif error.get("type") == "MultipleFrameworkIds":
        helper = ". Manually shut them down using 'dcos service shutdown'"
        error_message = error.get("message") + helper
    elif error.get("type") == "JsonSchemaMismatch":
        error_message = _format_json_schema_mismatch_message(error)
    elif error.get("type") == "MarathonBadResponse":
        error_message = _format_marathon_bad_response_message(error)
    else:
        error_message = error.get("message")

    return error_message


def _format_json_schema_mismatch_message(error):
    """Returns the formatted error message for JsonSchemaMismatch

    :param error: cosmos JsonSchemaMismatch error
    :type error: dict
    :returns: formatted error
    :rtype: str
    """

    error_messages = ["Error: {}".format(error.get("message"))]
    for err in error.get("data").get("errors"):
        if err.get("unwanted"):
            reason = "Unexpected properties: {}".format(err["unwanted"])
            error_messages += [reason]
        if err.get("found"):
            found = "Found: {}".format(err["found"])
            error_messages += [found]
        if err.get("expected"):
            expected = "Expected: {}".format(",".join(err["expected"]))
            error_messages += [expected]
        if err.get("instance"):
            pointer = err["instance"].get("pointer")
            formatted_path = pointer.lstrip("/").replace("/", ".")
            path = "Path: {}".format(formatted_path)
            error_messages += [path]

    error_messages += [
        "\nPlease create a JSON file with the appropriate options, and"
        " pass the /path/to/file as an --options argument."
    ]

    return "\n".join(error_messages)


def _format_marathon_bad_response_message(error):
    data = error.get("data")
    error_messages = [error.get("message")]
    if data is not None:
        for err in data.get("errors"):
            if (err.get("error") and
                    isinstance(err["error"], six.string_types)):
                error_messages += [err["error"]]
            elif err.get("errors") and \
                    isinstance(err["errors"], collections.Sequence):
                error_messages += err["errors"]
    return "\n".join(error_messages)


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
