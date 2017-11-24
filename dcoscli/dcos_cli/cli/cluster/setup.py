"""Defines the `dcos cluster setup` subcommand."""

import click


@click.command(name='setup')
def cluster_setup():
    """Set up a cluster."""
    print('Setup a cluster.')
