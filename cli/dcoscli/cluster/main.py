import os

import docopt

import dcoscli
from dcos import cluster, cmds, config, constants, emitting, http, util
from dcos.errors import DCOSAuthenticationException, DCOSException
from dcoscli.auth.main import login
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage


emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("cluster"),
        argv=argv,
        version='dcos-cluster version {}'.format(dcoscli.version))

    http.silence_requests_warnings()

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: all the supported commands
    :rtype: list of dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['cluster', 'setup'],
            arg_keys=['<dcos_url>',
                      '--password', '--password-env', '--password-file',
                      '--provider', '--username', '--private-key'],
            function=_setup),

        cmds.Command(
            hierarchy=['cluster'],
            arg_keys=['--info'],
            function=_info),
    ]


def _info(info):
    """
    :param info: Whether to output a description of this subcommand
    :type info: boolean
    :returns: process status
    :rtype: int
    """

    emitter.publish(default_command_info("cluster"))
    return 0


def _setup(dcos_url, password_str, password_env, password_file,
           provider, username, key_path):
    """
    Setup the CLI to talk to your DC/OS cluster.

    :param dcos_url: master ip of cluster
    :type dcos_url: str
    :param password_str: password
    :type password_str: str
    :param password_env: name of environment variable with password
    :type password_env: str
    :param password_file: path to file with password
    :type password_file: bool
    :param provider: name of provider to authentication with
    :type provider: str
    :param username: username
    :type username: str
    :param key_path: path to file with private key
    :type param: str
    :returns: process status
    :rtype: int
    """

    with cluster.setup_directory() as temp_path:

        # set cluster as attached
        util.ensure_file_exists(os.path.join(
            temp_path, constants.DCOS_CLUSTER_ATTACHED_FILE))

        # authenticate
        config.set_val("core.dcos_url", dcos_url)
        # get validated dcos_url
        dcos_url = config.get_config_val("core.dcos_url")
        try:
            login(dcos_url,
                  password_str, password_env, password_file,
                  provider, username, key_path)
        except DCOSAuthenticationException:
            msg = ("Authentication failed. "
                   "Please run `dcos cluster setup <dcos_url>`")
            raise DCOSException(msg)

        # configure cluster directory
        cluster_path = cluster.setup_cluster_config(dcos_url)
        cluster.set_attached(cluster_path)

    return 0
