"""Defines the `dcos config show` subcommand."""

import click


@click.command(name='show')
def config_show():
    """Print the configuration."""
    print('Show a config.')
