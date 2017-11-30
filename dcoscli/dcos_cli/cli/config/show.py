"""Defines the `dcos config show` subcommand."""

import click

from dcoscli.config.main import _show


@click.command(name='show')
@click.argument('name', required=False)
def config_show(name):
    """Print the configuration."""
    _show(name)
