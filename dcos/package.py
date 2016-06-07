import collections

from dcos import emitting, subcommand, util
from dcos.errors import DCOSException

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()


def uninstall(pkg, package_name, remove_all, app_id, cli, app):
    """Uninstalls a package.

    :param pkg: package manager to uninstall with
    :type pkg: PackageManager
    :param package_name: The package to uninstall
    :type package_name: str
    :param remove_all: Whether to remove all instances of the named app
    :type remove_all: boolean
    :param app_id: App ID of the app instance to uninstall
    :type app_id: str
    :param init_client: The program to use to run the app
    :type init_client: object
    :rtype: None
    """

    if cli is False and app is False:
        cli = app = True

    uninstalled = False
    installed = installed_packages(pkg, app_id, package_name)
    installed_cli = next((True for installed_pkg in installed
                          if installed_pkg.get("command")), False)
    installed_app = next((True for installed_pkg in installed
                          if installed_pkg.get("apps")), False)

    if cli and installed_cli:
        if subcommand.uninstall(package_name):
            uninstalled = True

    if app and installed_app:
        if pkg.uninstall_app(package_name, remove_all, app_id):
            uninstalled = True

    if uninstalled:
        return None
    else:
        msg = 'Package [{}]'.format(package_name)
        if app_id is not None:
            app_id = util.normalize_app_id(app_id)
            msg += " with id [{}]".format(app_id)
        msg += " is not installed"
        raise DCOSException(msg)


def uninstall_subcommand(distribution_name):
    """Uninstalls a subcommand.

    :param distribution_name: the name of the package
    :type distribution_name: str
    :returns: True if the subcommand was uninstalled
    :rtype: bool
    """

    return subcommand.uninstall(distribution_name)


class InstalledPackage(object):
    """Represents an intalled DC/OS package.  One of `app` and
    `subcommand` must be supplied.

    :param apps: A dictionary representing a marathon app. Of the
                format returned by `installed_apps()`
    :type apps: [dict]
    :param subcommand: Installed subcommand
    :type subcommand: subcommand.InstalledSubcommand
    """

    def __init__(self, apps=[], subcommand=None):
        assert apps or subcommand
        self.apps = apps
        self.subcommand = subcommand

    def name(self):
        """
        :returns: The name of the package
        :rtype: str
        """
        if self.subcommand:
            return self.subcommand.name
        else:
            return self.apps[0]['name']

    def dict(self):
        """ A dictionary representation of the package.  Used by `dcos package
        list`.

        :returns: A dictionary representation of the package.
        :rtype: dict
        """
        ret = {}

        if self.subcommand:
            ret['command'] = {'name': self.subcommand.name}

        if self.apps:
            ret['apps'] = sorted([app['appId'] for app in self.apps])

        if self.subcommand:
            package_json = self.subcommand.package_json()
            ret.update(package_json)
        else:
            ret.update(self.apps[0])
            ret.pop('appId')

        return ret


def _matches_package_name(name, command_name):
    """
    :param name: the name of the package
    :type name: str
    :param command_name: the name of the command
    :type command_name: str
    :returns: True if the name is not defined or the package matches that name;
              False otherwise
    :rtype: bool
    """

    return name is None or command_name == name


def installed_packages(package_manager, app_id, package_name):
    """Returns all installed packages in the format:

    [{
       'apps': [<id>],
       'command': {
         'name': <name>
       }
       ...<metadata>...
    }]

    :param init_client: The program to use to list packages
    :type init_client: object
    :param app_id: App ID of app to show
    :type app_id: str
    :param package_name: The package to show
    :type package_name: str
    :returns: A list of installed packages matching criteria
    :rtype: [dict]
    """

    dicts = collections.defaultdict(lambda: {'apps': [], 'command': None})

    apps = package_manager.installed_apps(package_name, app_id)
    for app in apps:
        key = app['name']
        dicts[key]['apps'].append(app)

    subcommands = installed_subcommands()
    for subcmd in subcommands:
        if _matches_package_name(package_name, subcmd.name):
            dicts[subcmd.name]['command'] = subcmd

    installed = [
        InstalledPackage(pkg['apps'], pkg['command']) for pkg in dicts.values()
    ]

    return [pkg.dict() for pkg in installed]


def installed_subcommands():
    """Returns all installed subcommands.

    :returns: all installed subcommands
    :rtype: [InstalledSubcommand]
    """

    return [subcommand.InstalledSubcommand(name) for name in
            subcommand.distributions()]
