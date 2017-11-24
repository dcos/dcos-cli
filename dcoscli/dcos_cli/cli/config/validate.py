"""Defines the `dcos config validate` subcommand."""

import click


@click.command(name='validate')
def config_validate():
    """Validate changes to the configuration."""
    print('Validate configuration.')
