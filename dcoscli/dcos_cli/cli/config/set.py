"""Defines the `dcos config set` subcommand."""

import click


@click.command(name='set')
def config_set():
    """Add or set a configuration property."""
    print('Set a config.')
