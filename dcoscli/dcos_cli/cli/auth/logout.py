"""Defines the `dcos auth logout` subcommand."""

import click


@click.command(name='logout')
def auth_logout():
    """Logout of your DC/OS cluster."""
    print('Logout of your DC/OS cluster.')
