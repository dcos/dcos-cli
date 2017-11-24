"""Defines the `dcos cluster rename` subcommand."""

import click


@click.command(name='rename')
def cluster_rename():
    """Rename a cluster."""
    print('Rename a cluster.')
