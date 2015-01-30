"""
Usage:
    dcos package info
    dcos package sources list
    dcos package update
    dcos package configure <package_name>
    dcos package search <query>
    dcos package install <package_name>
    dcos package uninstall <package_name>
    dcos package list

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
from dcos.api import config, constants, options, package


def main():
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    args = docopt.docopt(
        __doc__,
        version='dcos-marathon version {}'.format(constants.version))

    if args['package'] and args['info']:
        return _info()

    elif args['package'] and args['sources'] and args['list']:
        cfg = config.load_from_path(config_path)
        return _list_sources(cfg)

    elif args['package'] and args['update']:
        cfg = config.load_from_path(config_path)
        return _update(cfg)

    elif args['package'] and args['configure']:
        mutable_cfg = config.mutable_load_from_path(config_path)
        return _configure(args['<package_name>'], mutable_cfg)

    else:
        print(options.make_generic_usage_error(__doc__))
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
