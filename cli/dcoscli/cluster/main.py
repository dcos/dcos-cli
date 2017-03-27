import os

import docopt

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

import dcoscli

from dcos import cluster, cmds, config, emitting, http, util
from dcos.errors import DCOSAuthenticationException, DCOSException
from dcoscli.auth.main import login
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import confirm, decorate_docopt_usage


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
                      '--insecure', '--no-check', '--ca-certs',
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


def _setup(dcos_url,
           insecure, no_check, ca_certs,
           password_str, password_env, password_file,
           provider, username, key_path):
    """
    Setup the CLI to talk to your DC/OS cluster.

    :param dcos_url: master ip of cluster
    :type dcos_url: str
    :param insecure: whether or not to verify ssl certs
    :type insecure: bool
    :param no_check: whether or not to verify downloaded ca cert
    :type no_check: bool
    :param ca_certs: path to root CA to verify requests
    :type ca_certs: str
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
        cluster.set_attached(temp_path)

        # authenticate
        config.set_val("core.dcos_url", dcos_url)
        # get validated dcos_url
        dcos_url = config.get_config_val("core.dcos_url")

        # configure ssl settings
        stored_cert = False
        if insecure:
            config.set_val("core.ssl_verify", "false")
        elif ca_certs:
            config.set_val("core.ssl_verify", ca_certs)
        else:
            cert = cluster.get_cluster_cert(dcos_url)
            stored_cert = _store_cluster_cert(cert, no_check)

        try:
            login(dcos_url,
                  password_str, password_env, password_file,
                  provider, username, key_path)
        except DCOSAuthenticationException:
            msg = ("Authentication failed. "
                   "Please run `dcos cluster setup <dcos_url>`")
            raise DCOSException(msg)

        # configure cluster directory
        cluster.setup_cluster_config(dcos_url, temp_path, stored_cert)

    return 0


def _user_cert_validation(cert_str):
    """Prompt user for validation of certification from cluster

    :param cert_str: cluster certificate bundle
    :type cert_str: str
    :returns whether or not user validated cert
    :rtype: bool
    """

    cert = x509.load_pem_x509_certificate(
        cert_str.encode('utf-8'), default_backend())
    fingerprint = cert.fingerprint(hashes.SHA256())
    pp_fingerprint = ":".join("{:02x}".format(c) for c in fingerprint).upper()

    msg = "SHA256 fingerprint of cluster certificate bundle:\n{}".format(
            pp_fingerprint)

    return confirm(msg, False)


def _store_cluster_cert(cert, no_check):
    """Store cluster certificate bundle downloaded from cluster and store
    settings in core.ssl_verify

    :param cert: ca cert from cluster
    :type cert: str
    :param no_check: whether to verify downloaded cert
    :type no_check: bool
    :returns: whether or not we are storing the downloaded cert bundle
    :rtype: bool
    """

    if not no_check:
        if not _user_cert_validation(cert):
            # we don't have a cert, but we still want to validate SSL
            config.set_val("core.ssl_verify", "true")
            return False

    with util.temptext() as temp_file:
        _, temp_path = temp_file

        with open(temp_path, 'w') as f:
            f.write(cert)

        cert_path = os.path.join(
            config.get_attached_cluster_path(), "dcos_ca.crt")

        util.sh_copy(temp_path, cert_path)

    config.set_val("core.ssl_verify", cert_path)
    return True
