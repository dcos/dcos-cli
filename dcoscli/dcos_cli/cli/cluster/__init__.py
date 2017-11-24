import click

from .attach import cluster_attach
from .list import cluster_list
from .remove import cluster_remove
from .rename import cluster_rename
from .setup import cluster_setup


@click.group()
def cluster():
    """Manage your DC/OS clusters."""
    pass


cluster.add_command(cluster_attach)
cluster.add_command(cluster_list)
cluster.add_command(cluster_remove)
cluster.add_command(cluster_rename)
cluster.add_command(cluster_setup)
