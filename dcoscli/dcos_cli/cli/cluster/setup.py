"""Defines the `dcos cluster setup` subcommand."""

import click


# pylint: disable=too-many-arguments

@click.command(name='setup')
@click.option(
    '--ca-certs',
    type=click.Path(exists=True),
    help='Specify the path to a CA bundle to verify requests against.'
)
@click.option(
    '--insecure',
    is_flag=True,
    help='Allow requests to bypass SSL certificate verification (insecure).'
)
@click.option(
    '--no-check',
    is_flag=True,
    help='Do not check CA certficate downloaded from cluster (insecure).'
)
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
def cluster_setup(ca_certs, insecure, no_check, password, password_env,
                  password_file, private_key, provider, username):
    """Set up a cluster."""
    # pylint: disable=unused-argument
    print('Setup a cluster.')
