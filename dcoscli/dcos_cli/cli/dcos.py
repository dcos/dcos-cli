"""The CLI for DC/OS."""

import importlib
import logging
import os
import sys

import click

from dcos import (cluster, config, constants, emitting, errors)
from dcos import errors
from dcos_cli import __version__


logger = logging.getLogger(__name__)
emitter = emitting.FlatEmitter()

class DCOSCLI(click.MultiCommand):
    """The main `dcos` command."""

    def list_commands(self, ctx):
        """Return the list of available DC/OS commands."""
        return ['cluster', 'auth', 'config']

    def get_command(self, ctx, cmd_name):
        """Get a given command."""
        try:
            cmd = importlib.import_module('dcos_cli.cli.'+cmd_name)
        except ModuleNotFoundError:
            return None

        return getattr(cmd, cmd_name, None)

    def __call__(self, *args, **kwargs):
        """
        Invoke the CLI, it calls the command in `standalone_mode`.

        Click exception handling is disabled, the return value of the command
        is considered as the exit code.
        """
        try:
            code = self.main(standalone_mode=False, *args, **kwargs)
            sys.exit(code)
        except errors.DCOSException as e:
            click.echo(e, err=True)
            sys.exit(1)
        except click.ClickException as e:
            e.show()
            sys.exit(e.exit_code)
        except (EOFError, KeyboardInterrupt):
            sys.exit(1)


@click.command(cls=DCOSCLI)
@click.option('--debug', is_flag=True, help="Enable debug mode.")
@click.version_option(__version__, message='dcoscli.version=%(version)s')
def dcos(debug):
    """Run the dcos command."""
    if config.uses_deprecated_config():
        if constants.DCOS_CONFIG_ENV in os.environ:
            msg = ('{} is deprecated, please consider using '
                   '`dcos cluster setup <dcos_url>`.')
            err = errors.DefaultError(msg.format(constants.DCOS_CONFIG_ENV))
            emitter.publish(err)

        cluster.move_to_cluster_config()

    assert isinstance(debug, bool)
