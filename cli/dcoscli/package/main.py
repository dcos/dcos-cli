"""
Usage:
    dcos package describe <package_name>
    dcos package info
    dcos package install [--options=<options_file> --app-id=<app_id>]
         <package_name>
    dcos package list
    dcos package search <query>
    dcos package sources
    dcos package uninstall [--all | --app-id=<app-id>] <package_name>
    dcos package update

Options:
    -h, --help          Show this screen
    --version           Show version

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
import toml
from dcos.api import (cmds, config, constants, emitting, marathon, options,
                      package, util)

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-package version {}'.format(dcoscli.version))

    if not args['package']:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

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
            hierarchy=['info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['sources'],
            arg_keys=[],
            function=_list_sources),

        cmds.Command(
            hierarchy=['update'],
            arg_keys=[],
            function=_update),

        cmds.Command(
            hierarchy=['describe'],
            arg_keys=['<package_name>'],
            function=_describe),

        cmds.Command(
            hierarchy=['install'],
            arg_keys=['<package_name>', '--options', '--app-id'],
            function=_install),

        cmds.Command(
            hierarchy=['list'],
            arg_keys=[],
            function=_list),

        cmds.Command(
            hierarchy=['search'],
            arg_keys=['<query>'],
            function=_search),

        cmds.Command(
            hierarchy=['uninstall'],
            arg_keys=['<package_name>', '--all', '--app-id'],
            function=_uninstall),
    ]


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

    emitter.publish('Install and manage DCOS software packages')
    return 0


def _list_sources():
    """List configured package sources.

    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    sources, errors = package.list_sources(config)

    if len(errors) > 0:
        for err in errors:
            emitter.publish(err)
        return 1

    for source in sources:
        emitter.publish("{} {}".format(source.hash(), source.url))

    return 0


def _update():
    """Update local package definitions from sources.

    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    errors = package.update_sources(config)

    if len(errors) > 0:
        for err in errors:
            emitter.publish(err)
        return 1

    return 0


def _describe(package_name):
    """Describe the specified package.

    :param package_name: The package to configure
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

    emitter.publish(toml.dumps(pkg_json))
    emitter.publish('Available versions:')

    version_map, version_error = pkg.software_versions()

    if version_error is not None:
        emitter.publish(version_error)
        return 1

    for pkg_ver in version_map:
        emitter.publish(version_map[pkg_ver])

    return 0


def _install(package_name, options_file, app_id):
    """Install the specified package.

    :param package_name: The package to install
    :type package_name: str
    :param options_file: Path to file containing option values
    :type options_file: str
    :param app_id: App ID for installation of this package
    :type app_id: str
    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    pkg = package.resolve_package(package_name, config)

    if pkg is None:
        emitter.publish("Package [{}] not found".format(package_name))
        return 1

    options_json = {}

    if options_file is not None:
        try:
            options_fd = open(options_file)
            options_json = json.load(options_fd)
        except Exception as e:
            emitter.publish(e.message)
            return 1

    init_client = marathon.create_client(config)

    # TODO(CD): Make package version to install configurable
    pkg_version, version_error = pkg.latest_version()

    if version_error is not None:
        emitter.publish(version_error)
        return 1

    install_error = package.install(
        pkg,
        pkg_version,
        init_client,
        options_json,
        app_id,
        config)

    if install_error is not None:
        emitter.publish(install_error)
        return 1

    return 0


def _list():
    """Describe the specified package.

    :returns: Process status
    :rtype: int
    """

    config = _load_config()

    init_client = marathon.create_client(config)
    installed, error = package.list_installed_packages(init_client)

    if error is not None:
        emitter.publish(error)
        return 1

    for name, version in installed:
        emitter.publish('{} [{}]'.format(name, version))

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
        init_client,
        config)

    if uninstall_error is not None:
        emitter.publish(uninstall_error)
        return 1

    return 0
