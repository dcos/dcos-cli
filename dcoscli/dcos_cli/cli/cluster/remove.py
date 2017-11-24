"""Defines the `dcos cluster remove` subcommand."""

import click


@click.command(name='remove')
def cluster_remove():
    """Remove cluster(s)."""
    print('Remove cluster(s).')
