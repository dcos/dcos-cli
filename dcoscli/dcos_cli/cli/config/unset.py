"""Defines the `dcos config unset` subcommand."""

import click


@click.command(name='unset')
def config_unset():
    """Remove a configuration property."""
    print('Unset a config.')
