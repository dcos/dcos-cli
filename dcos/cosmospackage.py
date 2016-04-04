import collections
import functools

import six
from dcos import emitting, http, util
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException, DCOSException,
                         DCOSHTTPException, DefaultError)

from six.moves import urllib

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()


class Cosmos():
    """Implementation of Package Manager using Cosmos"""

    def __init__(self, cosmos_url):
        self.cosmos_url = cosmos_url

    def enabled(self):
        """Returns whether or not cosmos is enabled on specified dcos cluter

        :rtype: bool
        """

        try:
            url = urllib.parse.urljoin(self.cosmos_url, 'capabilities')
            response = http.get(url,
                                headers=_get_capabilities_header())
        # return `Authentication failed` error messages
        except DCOSAuthenticationException:
            raise
        # Authorization errors mean endpoint exists, and user could be
        # authorized for the command specified, not this endpoint
        except DCOSAuthorizationException:
            return True
        # allow exception through so we can show user actual http exception
        # except 404, because then the url is fine, just not cosmos enabled
        except DCOSHTTPException as e:
            logger.exception(e)
            return e.status() != 404
        except Exception as e:
            logger.exception(e)
            return True

        return response.status_code == 200

    def install_app(self, pkg, options, app_id):
        """Installs a package's application

        :param pkg: the package to install
        :type pkg: CosmosPackageVersion
        :param options: user supplied package parameters
        :type options: dict
        :param app_id: app ID for installation of this package
        :type app_id: str
        :rtype: None
        """

        params = {"packageName": pkg.name(), "packageVersion": pkg.version()}
        if options is not None:
            params["options"] = options
        if app_id is not None:
            params["appId"] = app_id

        self.cosmos_post("install", params)

    def uninstall_app(self, package_name, remove_all, app_id):
        """Uninstalls an app.

        :param package_name: The package to uninstall
        :type package_name: str
        :param remove_all: Whether to remove all instances of the named app
        :type remove_all: boolean
        :param app_id: App ID of the app instance to uninstall
        :type app_id: str
        :returns: whether uninstall was successful or not
        :rtype: bool
        """

        params = {"packageName": package_name}
        if remove_all is True:
            params["all"] = True
        if app_id is not None:
            params["appId"] = app_id

        response = self.cosmos_post("uninstall", params)
        results = response.json().get("results")

        uninstalled_versions = []
        for res in results:
            version = res.get("packageVersion")
            if version not in uninstalled_versions:
                emitter.publish(
                    DefaultError(
                        'Uninstalled package [{}] version [{}]'.format(
                            res.get("packageName"),
                            res.get("packageVersion"))))
                uninstalled_versions += [res.get("packageVersion")]

                if res.get("postUninstallNotes") is not None:
                    emitter.publish(
                        DefaultError(res.get("postUninstallNotes")))

        return True

    def search_sources(self, query):
        """package search

        :param query: query to search
        :type query: str
        :returns: list of package indicies of matching packages
        :rtype: [packages]
        """
        response = self.cosmos_post("search", {"query": query})
        return response.json()

    def get_package_version(self, package_name, package_version):
        """Returns PackageVersion of specified package

        :param package_name: package name
        :type package_name: str
        :param package_version: version of package
        :type package_version: str | None
        :rtype: PackageVersion

        """

        return CosmosPackageVersion(package_name, package_version,
                                    self.cosmos_url)

    def installed_apps(self, package_name, app_id):
        """List installed packages

        {
            'appId': <appId>,
            ..<package.json properties>..
        }

        :param package_name: the optional package to list
        :type package_name: str
        :param app_id: the optional application id to list
        :type app_id: str
        :rtype: [dict]
        """

        params = {}
        if package_name is not None:
            params["packageName"] = package_name
        if app_id is not None:
            params["appId"] = app_id

        list_response = self.cosmos_post("list", params).json()

        packages = []
        for pkg in list_response['packages']:
            result = pkg['packageInformation']['packageDefinition']

            result['appId'] = pkg['appId']
            packages.append(result)

        return packages

    def get_repos(self):
        """List locations of repos

        :returns: the list of repos, in resolution order or list
        :rtype: dict
        """

        return self.cosmos_post("repository/list", params={}).json()

    def add_repo(self, name, package_repo, index):
        """Add package repo and update repo with new repo

        :param name: name to call repo
        :type name: str
        :param package_repo: location of repo to add
        :type package_repo: str
        :param index: index to add this repo
        :type index: int
        :returns: current repo list
        :rtype: dict
        """

        params = {"name": name, "uri": package_repo}
        if index is not None:
            params["index"] = index
        response = self.cosmos_post("repository/add", params=params)
        return response.json()

    def remove_repo(self, name):
        """Remove package repo and update repo

        :param name: name of repo to remove
        :type name: str
        :returns: current repo list
        :rtype: dict
        """

        params = {"name": name}
        response = self.cosmos_post("repository/delete", params=params)
        return response.json()

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

            :param response: response from cosmos
            :type response: Response
            :returns: Response or raises Exception
            :rtype: valid response
            """

            response = fn(*args, **kwargs)
            content_type = response.headers.get('Content-Type')
            if content_type is None:
                raise DCOSHTTPException(response)
            elif _get_header("error") in content_type:
                logger.debug("Error: {}".format(response.json()))
                error_msg = _format_error_message(response.json())
                raise DCOSException(error_msg)
            return response

        return check_for_cosmos_error

    @cosmos_error
    def cosmos_post(self, request, params):
        """Request to cosmos server

        :param request: type of request
        :type requet: str
        :param params: body of request
        :type params: dict
        :returns: Response
        :rtype: Response
        """

        url = urllib.parse.urljoin(self.cosmos_url,
                                   'package/{}'.format(request))
        try:
            response = http.post(url, json=params,
                                 headers=_get_cosmos_header(request))
            if not _check_cosmos_header(request, response):
                raise DCOSException(
                    "Server returned incorrect response type: {}".format(
                        response.headers))
        except DCOSAuthenticationException:
            raise
        except DCOSAuthorizationException:
            raise
        except DCOSHTTPException as e:
            # let non authentication responses be handled by `cosmos_error` so
            # we can expose errors reported by cosmos
            response = e.response

        return response


class CosmosPackageVersion():
    """Interface to a specific package version from cosmos"""

    def __init__(self, name, package_version, url):
        self._name = name
        self._cosmos_url = url

        params = {"packageName":  name}
        if package_version is not None:
            params["packageVersion"] = package_version
        response = Cosmos(url).cosmos_post("describe", params)

        package_info = response.json()
        self._package_json = package_info.get("package")
        self._package_version = package_version or \
            self._package_json.get("version")
        self._config_json = package_info.get("config")
        self._command_json = package_info.get("command")
        self._resource_json = package_info.get("resource")
        self._marathon_template = package_info.get("marathonMustache")

    def registry(self):
        """Cosmos only supports one registry right now, so default to cosmos

        :returns: registry
        :rtype: str
        """

        return "cosmos"

    def version(self):
        """Returns the package version.

        :returns: The version of this package
        :rtype: str
        """

        return self._package_version

    def name(self):
        """Returns the package name.

        :returns: The name of this package
        :rtype: str
        """

        return self._name

    def revision(self):
        """We aren't exposing revisions for cosmos right now, so make
           custom string.

        :returns: revision
        :rtype: str
        """
        return "cosmos" + self._package_version

    def cosmos_url(self):
        """
        Returns location of cosmos server

        :returns: revision
        :rtype: str
        """

        return self._cosmos_url

    def package_json(self):
        """Returns the JSON content of the package.json file.

        :returns: Package data
        :rtype: dict
        """

        return self._package_json

    def config_json(self):
        """Returns the JSON content of the config.json file.

        :returns: Package config schema
        :rtype: dict
        """

        return self._config_json

    def resource_json(self):
        """Returns the JSON content of the resource.json file.

        :returns: Package resources
        :rtype: dict
        """

        return self._resource_json

    def marathon_template(self):
        """Returns raw data from marathon.json

        :returns: raw data from marathon.json
        :rtype: str
        """

        return self._marathon_template

    def marathon_json(self, options):
        """Returns the JSON content of the marathon.json template, after
        rendering it with options.

        :param options: the template options to use in rendering
        :type options: dict
        :rtype: dict
        """

        params = {"packageName":  self._name}
        params["packageVersion"] = self._package_version
        params["options"] = options
        response = Cosmos(self._cosmos_url).cosmos_post("render", params)
        return response.json().get("marathonJson")

    def has_mustache_definition(self):
        """Dummy method since all packages in cosmos must have mustache
           definition.
        """

        return True

    def options(self, user_options):
        """Makes sure user supplied options are valid, and returns valid options

        :param options: the template options to use in rendering
        :type options: dict
        :rtype: dict
        """

        self.marathon_json(user_options)

        return user_options

    def has_cli_definition(self):
        """Returns true if the package defines a command; false otherwise.

        :rtype: bool
        """

        return self._command_json is not None or (
            self._resource_json and self._resource_json.get("cli"))

    def command_json(self):
        """Returns the JSON content of the command.json file.

        :returns: Package data
        :rtype: dict
        """

        return self._command_json

    def package_versions(self):
        """Returns a list of available versions for this package

        :returns: package version
        :rtype: []
        """

        params = {"packageName": self.name(), "includePackageVersions": True}
        response = Cosmos(self._cosmos_url).cosmos_post(
            "list-versions", params)

        return list(response.json().get("results").keys())


def _get_header(request_type):
    """Returns header str for talking with cosmos

    :param request_type: name of specified request (ie uninstall-request)
    :type request_type: str
    :returns: header information
    :rtype: str
    """

    return ("application/vnd.dcos.package.{}+json;"
            "charset=utf-8;version=v1").format(request_type)


def _get_cosmos_header(request_name):
    """Returns header fields needed for a valid request to cosmos

    :param request_name: name of specified request (ie uninstall)
    :type request_name: str
    :returns: dict of required headers
    :rtype: {}
    """

    request_name = request_name.replace("/", ".")
    return {"Accept": _get_header("{}-response".format(request_name)),
            "Content-Type": _get_header("{}-request".format(request_name))}


def _get_capabilities_header():
    """Returns header fields needed for a valid request to cosmos capabilities
    endpoint

    :returns: header information
    :rtype: str
    """
    header = "application/vnd.dcos.capabilities+json;charset=utf-8;version=v1"
    return {"Accept": header, "Content-Type": header}


def _check_cosmos_header(request_name, response):
    """Validate that cosmos returned correct header for request

    :param request_type: name of specified request (ie uninstall-request)
    :type request_type: str
    :param response: response object
    :type response: Response
    :returns: whether or not we got expected response
    :rtype: bool
    """

    request_name = request_name.replace("/", ".")
    rsp = "{}-response".format(request_name)
    return _get_header(rsp) in response.headers.get('Content-Type')


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

    :param error: cosmos JsonSchemMismatch error
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
            if err.get("error") and isinstance(err["error"], six.string_types):
                error_messages += [err["error"]]
            elif err.get("errors") and \
                    isinstance(err["errors"], collections.Sequence):
                error_messages += err["errors"]
    return "\n".join(error_messages)
