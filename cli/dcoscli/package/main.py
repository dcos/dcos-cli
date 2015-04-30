"""Install and manage DCOS software packages

Usage:
    dcos package --config-schema
    dcos package --info
    dcos package describe [--app --options=<file> --cli] <package_name>
    dcos package info
    dcos package install [--cli | [--app --app-id=<app_id]]
                         [--options=<file>]
                 <package_name>
    dcos package list-installed [--endpoints --app-id=<app-id> <package_name>]
    dcos package search [<query>]
    dcos package sources
    dcos package uninstall [--cli | [--app --app-id=<app-id> --all]]
                 <package_name>
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

import dcoscli
import docopt
import pkg_resources
from dcos import (cmds, emitting, errors, marathon, options, package,
                  subcommand, util)

logger = util.get_logger(__name__)

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
    :rtype: dcos.cmds.Command
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
            arg_keys=['<package_name>', '--cli', '--app', '--options'],
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
            arg_keys=['<package_name>', '--all', '--app-id', '--cli', '--app'],
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

    config = util.get_config()

    sources, err = package.list_sources(config)

    if err is not None:
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

    config = util.get_config()

    errs = package.update_sources(config, validate)

    if len(errs) > 0:
        for err in errs:
            emitter.publish(err)
        return 1

    return 0


def _describe(package_name, cli, app, options_path):
    """Describe the specified package.

    :param package_name: The package to describe
    :type package_name: str
    :returns: Process status
    :rtype: int
    """

    config = util.get_config()

    pkg, err = package.resolve_package(package_name, config)
    if err is not None:
        emitter.publish(err)
        return 1

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

    versions = [version_map[key] for key in version_map]

    del pkg_json['version']
    pkg_json['versions'] = versions

    if cli or app:
        user_options, err = _user_options(options_path)
        if err is not None:
            emitter.publish(err)
            return 1

        options, err = pkg.options(pkg_version, user_options)
        if err is not None:
            emitter.publish(err)
            return 1

        if cli:
            command_json, err = pkg.command_json(pkg_version, options)
            if err is not None:
                emitter.publish(err)
                return 1

            pkg_json['command'] = command_json

        if app:
            marathon_json, err = pkg.marathon_json(pkg_version, options)
            if err is not None:
                emitter.publish(err)
                return 1

            pkg_json['app'] = marathon_json

    emitter.publish(pkg_json)

    return 0


def _user_options(path):
    if path is None:
        return ({}, None)
    else:
        with open(path) as options_file:
            user_options, err = util.load_json(options_file)
            if err is not None:
                return (None, err)
            return (user_options, None)


def _install(package_name, options_path, app_id, cli, app):
    """Install the specified package.

    :param package_name: the package to install
    :type package_name: str
    :param options_path: path to file containing option values
    :type options_path: str
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

    config = util.get_config()

    pkg, err = package.resolve_package(package_name, config)
    if err is not None:
        emitter.publish(err)
        return 1

    if pkg is None:
        emitter.publish(
            errors.DefaultError(
                "Package [{}] not found".format(package_name)))
        emitter.publish(
            errors.DefaultError(
                "You may need to run 'dcos package update' to update your "
                "repositories"))
        return 1

    # TODO(CD): Make package version to install configurable
    pkg_version, version_error = pkg.latest_version()
    if version_error is not None:
        emitter.publish(version_error)
        return 1

    user_options, err = _user_options(options_path)
    if err is not None:
        emitter.publish(err)
        return 1

    try:
        options, err = pkg.options(pkg_version, user_options)
        if err is not None:
            emitter.publish(err)
            return 1
    except Exception as e:
        logger.exception('Exception while generating options')
        emitter.publish(errors.DefaultError(e))
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
            options,
            app_id)

        if install_error is not None:
            emitter.publish(install_error)
            return 1

    if cli and pkg.is_command_defined(pkg_version):
        # Install subcommand
        emitter.publish('Installing CLI subcommand for package [{}]'.format(
            pkg.name()))

        err = subcommand.install(pkg, pkg_version, options)
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

    config = util.get_config()

    init_client = marathon.create_client(config)

    installed, error = package.installed_packages(init_client, endpoints)
    if error is not None:
        emitter.publish(error)
        return 1

    results = []
    for pkg in installed:
        if not ((package_name and pkg.name() != package_name) or
                (app_id and pkg.app and pkg.app['appId'] != app_id)):
            result, err = pkg.dict()
            if err is not None:
                emitter.publish(err)
                return 1

            results.append(result)

    emitter.publish(results)

    return 0


def _search(query):
    """Search for matching packages.

    :param query: The search term
    :type query: str
    :returns: Process status
    :rtype: int
    """
    if not query:
        query = ''

    config = util.get_config()

    results, error = package.search(query, config)

    if error is not None:
        emitter.publish(error)
        return 1

    emitter.publish([r.as_dict() for r in results])

    return 0


def _uninstall(package_name, remove_all, app_id, cli, app):
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

    err = package.uninstall(package_name, remove_all, app_id, cli, app)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0
