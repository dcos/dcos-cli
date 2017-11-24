"""Defines the `dcos auth login` subcommand."""

import click


# pylint: disable=too-many-arguments

@click.command(name='login')
@click.option(
    '--password',
    help='Specify password on the command line (insecure).'
)
@click.option(
    '--password-env',
    help='Specify an environment variable name that contains the password.'
)
@click.option(
    '--password-file',
    type=click.Path(exists=True),
    help='Specify the path to a file that contains the password.'
)
@click.option(
    '--private-key',
    type=click.Path(exists=True),
    help='Specify the path to a file that contains the private key.'
)
@click.option(
    '--provider',
    help='Specify the authentication provider to use for login.'
)
@click.option(
    '--username',
    help='Specify the username for login.'
)
def auth_login(password, password_env, password_file, private_key,
               provider, username):
    """Login to your DC/OS cluster."""
    # pylint: disable=unused-argument
    print('Login to your DC/OS cluster.')
