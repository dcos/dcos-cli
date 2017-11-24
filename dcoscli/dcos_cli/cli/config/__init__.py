import click

from .set import config_set
from .show import config_show
from .unset import config_unset
from .validate import config_validate


@click.group()
def config():
    """Manage the DC/OS configuration file."""
    pass


config.add_command(config_show)
config.add_command(config_set)
config.add_command(config_validate)
config.add_command(config_unset)
