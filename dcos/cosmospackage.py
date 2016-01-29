import functools
import json

import pystache
from dcos import emitting, http, package, util
from dcos.errors import DCOSException, DCOSHTTPException

from six.moves import urllib

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()


class Cosmos(package.PackageManager):
    """Implementation of Package Manager using Cosmos"""

    def __init__(self, cosmos_url):
        self.cosmos_url = cosmos_url

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
        if remove_all is not None:
            params["all"] = True
        if app_id is not None:
            params["appId"] = app_id

        self.cosmos_post("uninstall", params)

        return True

    def search_sources(self, query):
        """package search

        :param query: query to search
        :type query: str
        :returns: list of package indicies of matching packages
        :rtype: [packages]
        """
        response = self.cosmos_post("search", {"query": query})
        return [response.json()]

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
            'packageSource': <source>,
            'releaseVersion': <release_version>,
            'endpoints' (optional): [{
                'host': <host>,
                'ports': <ports>,
            }],
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
            result['packageSource'] = (
                pkg['packageInformation']['packageSource']
            )
            result['releaseVersion'] = (
                pkg['packageInformation']['releaseVersion']
            )

            packages.append(result)

        return packages

    def update_sources(self, validate=False):
        """Update package sources

        We are deprecating this command since it doesn't make sense for cosmos.
        """

        emitter.publish("This command is deprecated")
        return 0

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
            if content_type is None or _get_header("error") in content_type:
                errors = response.json().get("errors")
                error_messages = [err.get("message") for err in errors]
                raise DCOSException(", ".join(error_messages))
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
                                   'v1/package/{}'.format(request))
        try:
            response = http.post(url, json=params,
                                 headers=_get_cosmos_header(request))
        except DCOSHTTPException as e:
            # let the response be handled by `cosmos_error` so we can expose
            # errors reported by cosmos
            response = e.response
        return response


class CosmosPackageVersion(package.PackageVersion):
    """Interface to a specific package version from cosmos"""

    def __init__(self, name, package_version, url):
        self._name = name
        self._cosmos_url = url

        params = {"packageName":  name}
        if package_version is not None:
            params += {"packageVersion": package_version}
        response = Cosmos(url).cosmos_post("describe", params)

        package_info = response.json()
        self._package_json = package_info.get("package")
        self._package_version = package_version or \
            self._package_json.get("version")
        self._config_json = package_info.get("config")
        self._command_json = package_info.get("command")
        self._resource_json = package_info.get("resource")
        self._marathon_template = package_info.get("marathonTemplate")

    def registry(self):
        """Cosmos only supports one registry right now, so default to cosmos

        :returns: registry
        :rtype: str
        """

        return "cosmos"

    def revision(self):
        """We aren't exposing revisions for cosmos right now, so make
           custom string.

        :returns: revision
        :rtype: str
        """
        return "cosmos" + self._package_version

    def cosmos_url(self):
        """
        Returns location of cosmos server from `DCOS_COSMOS_URL` env variable

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

    def _resource_json(self):
        """Returns the JSON content of the resource.json file.

        :returns: Package resources
        :rtype: dict
        """

        return self._resource_json

    def command_template(self):
        """ Returns raw data from command.json

        :returns: raw data from command.json
        :rtype: str
        """
        return json.dumps(self._command_json)

    def marathon_template(self):
        """Returns raw data from marathon.json

        :returns: raw data from marathon.json
        :rtype: str
        """

        return self._marathon_template

    def has_mustache_definition(self):
        """Dummy method since all packages in cosmos must have mustache
           definition.
        """

        return True

    def options(self, user_options):
        """Merges package options with user supplied options, validates, and
        returns the result.

        This will be /v1/package/render.
        For now pass, rendering will happen on server during install
        """

        return user_options

    def has_command_definition(self):
        """Returns true if the package defines a command; false otherwise.

        :rtype: bool
        """

        return self._command_json is not None

    def command_json(self, options):
        """Returns the JSON content of the command.json template, after
        rendering it with options.

        :param options: the template options to use in rendering
        :type options: dict
        :returns: Package data
        :rtype: dict
        """

        rendered = pystache.render(json.dumps(self._command_json), options)
        return util.load_jsons(rendered)

    def package_versions(self):
        """Returns a list of available versions for this package

        :returns: package version
        :rtype: []
        """

        params = {"packageName": self.name(), "packageVersions": True}
        response = Cosmos(self._cosmos_url).cosmos_post("describe", params)

        return list(response.json().keys())


def _get_header(request_type):
    """Returns header str for talking with cosmos

    :param request_type: name of specified request (ie uninstall-request)
    :type request_type: str
    :returns: header information
    :rtype: str
    """

    return ("application/vnd.dcos.cosmos.{}+json;"
            "charset=utf-8;version=v1").format(request_type)


def _get_cosmos_header(request_name):
    """Returns header fields needed for a valid request to cosmos

    :param request_name: name of specified request (ie uninstall)
    :type request_name: str
    :returns: dict of required headers
    :rtype: {}
    """

    return {"Accept": _get_header("{}-response".format(request_name)),
            "Content-Type": _get_header("{}-request".format(request_name))}
