"""Defines the `dcos cluster attach` subcommand."""

import click

from dcoscli.cluster.main import _attach


@click.command(name='attach')
@click.argument('name')
def cluster_attach(name):
    """Attach to a cluster."""
    return _attach(name)
