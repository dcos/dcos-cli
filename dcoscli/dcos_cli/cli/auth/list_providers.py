"""Defines the `dcos auth list-providers` subcommand."""

import click


@click.command(name='list-providers')
@click.option(
    '--json',
    help='List as JSON.'
)
@click.argument('url')
def auth_list_providers(url, json):
    """List authentication providers."""
    print('List authentication providers.')
