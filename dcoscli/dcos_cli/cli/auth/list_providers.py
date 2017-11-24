"""Defines the `dcos auth list-providers` subcommand."""

import click


@click.command(name='list-providers')
def auth_list_providers():
    """List authentication providers."""
    print('List authentication providers.')
