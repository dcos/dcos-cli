"""Defines the `dcos config validate` subcommand."""

import click

from dcoscli.config.main import _validate


@click.command(name='validate')
def config_validate():
    """Validate changes to the configuration."""
    _validate()
