"""Defines the `dcos cluster rename` subcommand."""

import click

from dcoscli.cluster.main import _rename


@click.command(name='rename')
@click.argument('name')
@click.argument('new_name')
def cluster_rename(name, new_name):
    """Rename a cluster."""
    return _rename(name, new_name)
