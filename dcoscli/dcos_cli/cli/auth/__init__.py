import click

from .login import auth_login
from .logout import auth_logout
from .list_providers import auth_list_providers


@click.group()
def auth():
    """Authenticate to your DC/OS cluster."""
    pass


auth.add_command(auth_list_providers)
auth.add_command(auth_login)
auth.add_command(auth_logout)
