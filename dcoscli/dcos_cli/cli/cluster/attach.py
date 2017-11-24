"""Defines the `dcos cluster attach` subcommand."""

import click


@click.command(name='attach')
def cluster_attach():
    """Attach to a cluster."""
    print('Attach to a cluster.')
