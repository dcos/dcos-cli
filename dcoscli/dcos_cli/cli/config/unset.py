"""Defines the `dcos config unset` subcommand."""

import click

from dcoscli.config.main import _unset


@click.command(name='unset')
@click.argument('name')
def config_unset(name):
    """Remove a configuration property."""
    _unset(name)
