"""Defines the `dcos cluster list` subcommand."""

import click

from dcoscli.cluster.main import _list


@click.command(name='list')
@click.option(
    '--attached',
    is_flag=True,
    help='List only the attached cluster.'
)
@click.option(
    '--json',
    is_flag=True,
    help='Print a JSON list.'
)
def cluster_list(attached, json):
    """List clusters."""
    return _list(json, attached)
