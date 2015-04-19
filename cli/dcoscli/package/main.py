"""Install and manage DCOS software packages

Usage:
    dcos package --config-schema
    dcos package --info
    dcos package describe <package_name>
    dcos package info
    dcos package install [--options=<file> --app-id=<app_id> --cli --app]
                 <package_name>
    dcos package list-installed [--endpoints --app-id=<app-id> <package_name>]
    dcos package search <query>
    dcos package sources
    dcos package uninstall [--all | --app-id=<app-id>] <package_name>
    dcos package update [--validate]

Options:
    -h, --help         Show this screen
    --info             Show a short description of this subcommand
    --version          Show version
    --all              Apply the operation to all matching packages
    --app              Apply the operation only to the package's application
    --app-id=<app-id>  The application id
    --cli              Apply the operation only to the package's CLI
    --options=<file>   Path to a JSON file containing package installation
                       options
    --validate         Validate package content when updating sources

Configuration:
    [package]
    # Path to the local package cache.
    cache_dir = "/var/dcos/cache"

    # List of package sources, in search order.
    #
    # Three protocols are supported:
    #   - Local file
    #   - HTTPS
    #   - Git
    sources = [
      "file:///Users/me/test-registry",
      "https://my.org/registry",
      "git://github.com/mesosphere/universe.git"
    ]
"""

import json
import os

import dcoscli
import docopt
import pkg_resources
from dcos.api import (cmds, config, constants, emitting, errors, marathon,
                      options, package, util)

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-package version {}'.format(dcoscli.version))

    returncode, err = cmds.execute(_cmds(), args)
    if err is not None:
        emitter.publish(err)
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return returncode


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: dcos.api.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['package', 'sources'],
            arg_keys=[],
            function=_list_sources),

        cmds.Command(
            hierarchy=['package', 'update'],
            arg_keys=['--validate'],
            function=_update),

        cmds.Command(
            hierarchy=['package', 'describe'],
            arg_keys=['<package_name>'],
            function=_describe),

        cmds.Command(
            hierarchy=['package', 'install'],
            arg_keys=['<package_name>', '--options', '--app-id', '--cli',
                      '--app'],
            function=_install),

        cmds.Command(
            hierarchy=['package', 'list-installed'],
            arg_keys=['--endpoints', '--app-id', '<package_name>'],
            function=_list),

        cmds.Command(
            hierarchy=['package', 'search'],
            arg_keys=['<query>'],
            function=_search),

        cmds.Command(
            hierarchy=['package', 'uninstall'],
            arg_keys=['<package_name>', '--all', '--app-id'],
            function=_uninstall),

        cmds.Command(
            hierarchy=['package'],
            arg_keys=['--config-schema', '--info'],
            function=_package),
    ]


def _package(config_schema, info):
    """
    :param config_schema: Whether to output the config schema
    :type config_schema: boolean
    :param info: Whether to output a description of this subcommand
    :type info: boolean
    :returns: Process status
    :rtype: int
    """

    if config_schema:
        schema = json.loads(
            pkg_resources.resource_string(
                'dcoscli',
                'data/config-schema/package.json').decode('utf-8'))
        emitter.publish(schema)
    elif info:
        _info()
    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return 0


def _load_config():
    """
    :returns: Configuration object
    :rtype: Toml
    """
    return config.load_from_path(
        os.environ[constants.DCOS_CONFIG_ENV])


def _info():
    """Print package cli information.

    :returns: Process status
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _list_sources():
    """List configured package sources.

    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    sources, errs = package.list_sources(config)

    if len(errs) > 0:
        for err in errs:
            emitter.publish(err)
        return 1

    for source in sources:
        emitter.publish("{} {}".format(source.hash(), source.url))

    return 0


def _update(validate):
    """Update local package definitions from sources.

    :param validate: Whether to validate package content when updating sources.
    :type validate: bool
    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    errs = package.update_sources(config, validate)

    if len(errs) > 0:
        for err in errs:
            emitter.publish(err)
        return 1

    return 0


def _describe(package_name):
    """Describe the specified package.

    :param package_name: The package to describe
    :type package_name: str
    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    pkg = package.resolve_package(package_name, config)

    if pkg is None:
        emitter.publish("Package [{}] not found".format(package_name))
        return 1

    # TODO(CD): Make package version to describe configurable
    pkg_version, version_error = pkg.latest_version()
    if version_error is not None:
        emitter.publish(version_error)
        return 1

    pkg_json, pkg_error = pkg.package_json(pkg_version)

    if pkg_error is not None:
        emitter.publish(pkg_error)
        return 1

    version_map, version_error = pkg.software_versions()

    if version_error is not None:
        emitter.publish(version_error)
        return 1

    versions = [version_map[pkg_ver] for pkg_ver in version_map]

    del pkg_json['version']
    pkg_json['versions'] = versions
    emitter.publish(pkg_json)

    return 0


def _install(package_name, options_file, app_id, cli, app):
    """Install the specified package.

    :param package_name: the package to install
    :type package_name: str
    :param options_file: path to file containing option values
    :type options_file: str
    :param app_id: app ID for installation of this package
    :type app_id: str
    :param cli: indicates if the cli should be installed
    :type cli: bool
    :param app: indicate if the application should be installed
    :type app: bool
    :returns: process status
    :rtype: int
    """

    if cli is False and app is False:
        # Install both if neither flag is specified
        cli = True
        app = True

    config = _load_config()

    pkg = package.resolve_package(package_name, config)
    if pkg is None:
        emitter.publish(
            errors.DefaultError(
                "Package [{}] not found".format(package_name)))
        emitter.publish(
            errors.DefaultError(
                "You may need to run 'dcos package update' to update your "
                "repositories"))
        return 1

    options_json = {}

    if options_file is not None:
        try:
            options_fd = open(options_file)
            options_json = json.load(options_fd)
        except Exception as e:
            emitter.publish(e.message)
            return 1

    # TODO(CD): Make package version to install configurable
    pkg_version, version_error = pkg.latest_version()

    if version_error is not None:
        emitter.publish(version_error)
        return 1

    if app:
        # Install in Marathon
        version_map, version_error = pkg.software_versions()

        if version_error is not None:
            emitter.publish(version_error)
            return 1

        sw_version = version_map.get(pkg_version, '?')

        message = 'Installing package [{}] version [{}]'.format(
            pkg.name(), sw_version)
        if app_id is not None:
            message += ' with app id [{}]'.format(app_id)

        emitter.publish(message)

        init_client = marathon.create_client(config)

        install_error = package.install_app(
            pkg,
            pkg_version,
            init_client,
            options_json,
            app_id)
        if install_error is not None:
            emitter.publish(install_error)
            return 1

    if cli and pkg.is_command_defined(pkg_version):
        # Install subcommand
        emitter.publish('Installing CLI subcommand for package [{}]'.format(
            pkg.name()))

        err = package.install_subcommand(pkg, pkg_version, options_json)
        if err is not None:
            emitter.publish(err)
            return 1

    return 0


def _list(endpoints, app_id, package_name):
    """Show installed apps

    :param endpoints: Whether to include a list of
        endpoints as port-host pairs
    :type endpoints: boolean
    :param package_name: The package to show
    :type package_name: str
    :param app_id: App ID of app to show
    :type app_id: str
    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    init_client = marathon.create_client(config)

    def keep(pkg):
        if package_name and pkg.get('name', '') != package_name:
            return False
        if app_id and pkg.get('appId', '') != app_id:
            return False
        return True

    installed, error = package.list_installed_packages(init_client, keep)

    if error is not None:
        emitter.publish(error)
        return 1

    if endpoints:
        installed, error = package.get_tasks_multiple(init_client, installed)
        if error is not None:
            emitter.publish(error)
            return 1

    emitter.publish(installed)

    return 0


def _search(query):
    """Search for matching packages.

    :param query: The search term
    :type query: str
    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    results, error = package.search(query, config)

    if error is not None:
        emitter.publish(error)
        return 1

    emitter.publish([r.as_dict() for r in results])

    return 0


def _uninstall(package_name, remove_all, app_id):
    """Uninstall the specified package.

    :param package_name: The package to uninstall
    :type package_name: str
    :param remove_all: Whether to remove all instances of the named package
    :type remove_all: boolean
    :param app_id: App ID of the package instance to uninstall
    :type app_id: str
    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    init_client = marathon.create_client(config)

    uninstall_error = package.uninstall(
        package_name,
        remove_all,
        app_id,
        init_client)

    if uninstall_error is not None:
        emitter.publish(uninstall_error)
        return 1

    return 0
