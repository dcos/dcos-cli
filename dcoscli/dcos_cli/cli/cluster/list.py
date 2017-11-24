"""Defines the `dcos cluster list` subcommand."""


import click


@click.command(name='list')
def cluster_list():
    """List clusters."""
    print('List clusters.')
