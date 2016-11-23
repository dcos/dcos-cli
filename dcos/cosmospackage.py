import base64

from six.moves import urllib

from dcos import cosmos, emitting, http, util
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException,
                         DCOSHTTPException, DefaultError)

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


class Cosmos():
    """Implementation of Package Manager using Cosmos"""

    def __init__(self, cosmos_url):
        self.cosmos_url = cosmos_url
        self.cosmos = cosmos.Cosmos(self.cosmos_url)

    def has_capability(self, capability):
        """Check if cluster has a capability.

        :param capability: capability name
        :type capability: string
        :return: does the cluster has capability
        :rtype: bool
        """

        if not self.enabled():
            return False

        try:
            url = urllib.parse.urljoin(self.cosmos_url, 'capabilities')
            response = http.get(url,
                                headers=_get_capabilities_header()).json()
        except Exception as e:
            logger.exception(e)
            return False

        if 'capabilities' not in response:
            logger.error(
                'Request to get cluster capabilities: {} '
                'returned unexpected response: {}. '
                'Missing "capabilities" field'.format(url, response))
            return False

        return {'name': capability} in response['capabilities']

    def enabled(self):
        """Returns whether or not cosmos is enabled on specified dcos cluster

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
        self.cosmos.package_install(
            pkg.name(), pkg.version(), options, app_id)

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
        response = self.cosmos.package_uninstall(
            package_name, app_id, remove_all)
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
        return self.cosmos.package_search(query).json()

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
        response = self.cosmos.package_list(package_name, app_id).json()

        packages = []
        for pkg in response['packages']:
            result = pkg['packageInformation']['packageDefinition']

            result['appId'] = pkg['appId']
            packages.append(result)

        return packages

    def get_repos(self):
        """List locations of repos

        :returns: the list of repos, in resolution order or list
        :rtype: dict
        """
        return self.cosmos.package_repository_list().json()

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
        return self.cosmos.package_repository_add(
            name, package_repo, index).json()

    def remove_repo(self, name):
        """Remove package repo and update repo

        :param name: name of repo to remove
        :type name: str
        :returns: current repo list
        :rtype: dict
        """
        return self.cosmos.package_repository_delete(name).json()

    def package_add(self, dcos_package):
        """
        Adds a DC/OS package to DC/OS

        :param dcos_package: path to the DC/OS package
        :type dcos_package: str
        :return: Response to the package add request
        :rtype: Response
        """
        return self.cosmos.package_add(dcos_package)


class CosmosPackageVersion():
    """Interface to a specific package version from cosmos"""

    def __init__(self, name, package_version, url):
        self._name = name
        self._cosmos_url = url
        self._cosmos = cosmos.Cosmos(self._cosmos_url)

        package_info = self._cosmos.package_describe(
            name, package_version).json()

        self._config_json = package_info.get("config")
        self._command_json = package_info.get("command")
        self._resource_json = package_info.get("resource")

        if package_info.get("marathonMustache") is not None:
            self._marathon_template = package_info["marathonMustache"]
        else:
            self._marathon_template = package_info.get("marathon")
            if self._marathon_template is not None:
                self._marathon_template = base64.b64decode(
                    self._marathon_template.get("v2AppMustacheTemplate")
                ).decode('utf-8')

        if package_info.get("package") is not None:
            self._package_json = package_info["package"]
            self._package_version = self._package_json["version"]
        else:
            self._package_json = _v2_package_to_v1_package_json(package_info)
            self._package_version = self._package_json["version"]

        self._package_version = \
            package_version or self._package_json.get("version")

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
        return self._cosmos.package_render(
            self._name, self._package_version, options
        ).json().get('marathonJson')

    def has_mustache_definition(self):
        """Returns True if packages has a marathon template

        :rtype: bool
        """

        return self._marathon_template is not None

    def options(self, user_options):
        """Makes sure user supplied options are valid

        :param user_options: the template options to use in rendering
        :type user_options: dict
        :rtype: None
        """

        self.marathon_json(user_options)
        return None

    def has_cli_definition(self):
        """Returns true if the package defines a command; false otherwise.

        :rtype: bool
        """

        return self._command_json is not None or (
            self._resource_json and self._resource_json.get("cli"))

    def cli_definition(self):
        """Returns the JSON content that defines a cli subcommand. Looks for
        "cli" property in resource.json first and if that is None, checks for
        command.json

        :returns: Package data
        :rtype: dict
        """

        return (self._resource_json and self._resource_json.get("cli")) or (
            self._command_json)

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
        response = self._cosmos.package_list_versions(self.name()).json()
        return list(response.get('results').keys())


def _get_capabilities_header():
    """Returns header fields needed for a valid request to cosmos capabilities
    endpoint
    :returns: header information
    :rtype: str
    """
    header = "application/vnd.dcos.capabilities+json;charset=utf-8;version=v1"
    return {"Accept": header, "Content-Type": header}


def _v2_package_to_v1_package_json(package_info):
    """Convert v2 package information to only contain info consumed by
    package.json

    :param package_info: package information
    :type package_info: dict
    :rtype {}
    """
    package_json = package_info
    if "command" in package_json:
        del package_json["command"]
    if "config" in package_json:
        del package_json["config"]
    if "marathon" in package_json:
        del package_json["marathon"]
    if "resource" in package_json:
        del package_json["resource"]

    return package_json
