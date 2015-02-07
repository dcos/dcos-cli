"""
Usage:
    dcos package describe <package_name>
    dcos package info
    dcos package install [--options=<options_file>] <package_name>
    dcos package list
    dcos package search <query>
    dcos package sources
    dcos package uninstall <package_name>
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
import logging
import os

import docopt
import toml
from dcos.api import config, constants, marathon, options, package


def main():
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    args = docopt.docopt(
        __doc__,
        version='dcos-package version {}'.format(constants.version))

    if args['package'] and args['info']:
        return _info()

    elif args['package'] and args['sources']:
        cfg = config.load_from_path(config_path)
        return _list_sources(cfg)

    elif args['package'] and args['update']:
        cfg = config.load_from_path(config_path)
        return _update(cfg)

    elif args['package'] and args['describe'] and args['<package_name>']:
        cfg = config.load_from_path(config_path)
        return _describe(args['<package_name>'], cfg)

    elif args['package'] and args['install']:
        cfg = config.load_from_path(config_path)
        return _install(args['<package_name>'], args['--options'], cfg)

    elif args['package'] and args['list']:
        cfg = config.load_from_path(config_path)
        return _list(cfg)

    else:
        print(options.make_generic_usage_message(__doc__))
        return 1


def _info():
    """Print package cli information.

    :returns: Process status
    :rtype: int
    """

    print('Install and manage DCOS software packages')
    return 0


def _list_sources(config):
    """List configured package sources.

    :param config: Configuration dictionary
    :type config: dcos.api.config.Toml
    :returns: Process status
    :rtype: int
    """

    sources, errors = package.list_sources(config)

    if len(errors) > 0:
        for err in errors:
            print(err.error())
        return 1

    for source in sources:
        print("{} {}".format(source.hash(), source.url))

    return 0


def _update(config):
    """Update local package definitions from sources.

    :param config: Configuration dictionary
    :type config: dcos.api.config.Toml
    :returns: Process status
    :rtype: int
    """

    errors = package.update_sources(config)

    if len(errors) > 0:
        for err in errors:
            print(err.error())
        return 1

    return 0


def _describe(package_name, config):
    """Describe the specified package.

    :param package_name: The package to configure
    :type package_name: str
    :param config: The config object
    :type config: dcos.api.config.Toml
    :returns: Process status
    :rtype: int
    """

    pkg = package.resolve_package(package_name, config)

    if pkg is None:
        print("Package [{}] not found".format(package_name))
        return 1

    # TODO(CD): Make package version to describe configurable
    pkg_version, version_error = pkg.latest_version()
    if version_error is not None:
        print(version_error.error())
        return 1

    pkg_json, pkg_error = pkg.package_json(pkg_version)

    if pkg_error is not None:
        print(pkg_error.error())
        return 1

    print(toml.dumps(pkg_json))
    print('Available versions:')

    version_map, version_error = pkg.software_versions()

    if version_error is not None:
        print(version_error.error())
        return 1

    for pkg_ver in version_map:
        print(version_map[pkg_ver])

    return 0


def _install(package_name, options_file, config):
    """Install the specified package.

    :param package_name: The package to install
    :type package_name: str
    :param options_file: Path to file containing option values
    :type options_file: str
    :param cfg: The config object to modify
    :type cfg: dcos.api.config.Toml
    :returns: Process status
    :rtype: int
    """

    pkg = package.resolve_package(package_name, config)

    if pkg is None:
        print("Package [{}] not found".format(package_name))
        return 1

    options_json = {}

    if options_file is not None:
        try:
            options_fd = open(options_file)
            options_json = json.load(options_fd)
        except Exception as e:
            print(e.message)
            return 1

    init_client = marathon.create_client(config)

    # TODO(CD): Make package version to install configurable
    pkg_version, version_error = pkg.latest_version()

    if version_error is not None:
        print(version_error.error())
        return 1

    install_error = package.install(
        pkg,
        pkg_version,
        init_client,
        options_json,
        config)

    if install_error is not None:
        print(install_error.error())
        return 1

    return 0


def _list(config):
    """Describe the specified package.

    :param config: The config object
    :type config: dcos.api.config.Toml
    :returns: Process status
    :rtype: int
    """

    init_client = marathon.create_client(config)
    installed, error = package.list_installed_packages(init_client)

    for name, version in installed:
        print('{} [{}]'.format(name, version))

    if error is not None:
        print(error.error())
        return 1

    return 0
