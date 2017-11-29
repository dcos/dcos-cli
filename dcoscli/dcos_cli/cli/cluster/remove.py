"""Defines the `dcos cluster remove` subcommand."""

import click

from dcoscli.cluster.main import _remove


@click.command(name='remove')
@click.option(
    '--all',
    'all_',  # not to conflict with the built-in function
    is_flag=True,
    help='Remove all configured clusters.'
)
@click.argument('name', required=False)
def cluster_remove(name, all_):
    """Remove cluster(s)."""
    return _remove(name, all_)
