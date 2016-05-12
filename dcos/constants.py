DCOS_DIR = ".dcos"
"""DCOS data directory.  Can store subcommands and the config file."""

DCOS_SUBCOMMAND_ENV_SUBDIR = 'env'
"""In a package's directory, this is the cli contents subdirectory."""

DCOS_SUBCOMMAND_SUBDIR = 'subcommands'
"""Name of the subdirectory that contains all of the subcommands. This is
relative to the location of the executable."""

DCOS_CONFIG_ENV = 'DCOS_CONFIG'
"""Name of the environment variable pointing to the DCOS config."""

DCOS_LOG_LEVEL_ENV = 'DCOS_LOG_LEVEL'
"""Name of the environment variable for the DCOS log level"""

DCOS_DEBUG_ENV = 'DCOS_DEBUG'
"""Name of the environment variable to enable DCOS debug messages"""

DCOS_PAGER_COMMAND_ENV = 'PAGER'
"""Command to use to page long command output (e.g. 'less -R')"""

DCOS_SSL_VERIFY_ENV = 'DCOS_SSL_VERIFY'
"""Whether or not ot verify SSL certs for HTTPS or path to certificate(s)"""

PATH_ENV = 'PATH'
"""Name of the environment variable pointing to the executable directories."""

DCOS_COMMAND_PREFIX = 'dcos-'
"""Prefix for all the DCOS CLI commands."""

VALID_LOG_LEVEL_VALUES = ['debug', 'info', 'warning', 'error', 'critical']
"""List of all the supported log level values for the CLIs"""
