"""
Usage:
    dcos package configure <package_name>
    dcos package describe <package_name>
    dcos package info
    dcos package install <package_name>
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

import logging
import os

import docopt
import toml
from dcos.api import config, constants, options, package


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

    elif args['package'] and args['configure']:
        mutable_cfg = config.mutable_load_from_path(config_path)
        return _configure(args['<package_name>'], mutable_cfg)

    else:
        print(options.make_generic_usage_message(__doc__))
        return 1


def _info():
    """Print package cli information.

    :returns: Process status
    :rtype: int
    """

    print('Install and manage DCOS software packages.')
    return 0


def _list_sources(config):
    """List configured package sources.

    :param config: Configuration dictionary
    :type config: config.Toml
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
    :type config: config.Toml
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
    :type config: config.Toml
    :returns: Process status
    :rtype: int
    """

    pkg = package.resolve_package(package_name, config)

    if pkg is None:
        print("Package [{}] not found".format(package_name))
        return 1

    pkg_json = pkg.package_json(pkg.latest_version())
    print(toml.dumps(pkg_json))
    return 0


def _configure(package_name, mutable_cfg):
    """Configure the specified package.

    :param package_name: The package to configure
    :type package_name: str
    :param mutable_cfg: The config object to modify
    :type mutable_cfg: config.MutableToml
    :returns: Process status
    :rtype: int
    """

    pkg, pkg_err = package.get_package(package_name)

    if pkg_err is not None:
        print(pkg_err.error())
        return 1

    success, err = package.configure(mutable_cfg)

    if err is not None:
        print(err.error())
        return 1

    return 0
