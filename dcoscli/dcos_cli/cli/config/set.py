"""Defines the `dcos config set` subcommand."""

import click

from dcoscli.config.main import _set


@click.command(name='set')
@click.argument('name')
@click.argument('value')
def config_set(name, value):
    """Add or set a configuration property."""
    return _set(name, value)
