"""Defines the `dcos auth logout` subcommand."""

import click

from dcoscli.auth.main import _logout


@click.command(name='logout')
def auth_logout():
    """Logout of your DC/OS cluster."""
    return _logout()
