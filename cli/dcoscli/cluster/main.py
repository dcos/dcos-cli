import os

import docopt
import requests

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

import dcoscli

from dcos import cluster, cmds, config, emitting, http, util
from dcos.errors import (DCOSAuthenticationException, DCOSException,
                         DefaultError)
from dcoscli.auth.main import login
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.tables import clusters_table
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
            function=setup),

        cmds.Command(
            hierarchy=['cluster', 'list'],
            arg_keys=['--json', '--attached'],
            function=_list),

        cmds.Command(
            hierarchy=['cluster', 'remove'],
            arg_keys=['<name>', '--all'],
            function=_remove),

        cmds.Command(
            hierarchy=['cluster', 'attach'],
            arg_keys=['<name>'],
            function=_attach),

        cmds.Command(
            hierarchy=['cluster', 'rename'],
            arg_keys=['<name>', '<new_name>'],
            function=_rename),

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


def _list(json_, attached):
    """
    List configured clusters.

    :param json_: output json if True
    :type json_: bool
    :param attached: return only attached cluster
    :type attached: True
    :rtype: None
    """

    clusters = [c.dict() for c in cluster.get_clusters()
                if not attached or c.is_attached()]
    if json_:
        emitter.publish(clusters)
    elif len(clusters) == 0:
        if attached:
            msg = ("No cluster is attached. "
                   "Please run `dcos cluster attach <cluster-name>")
        else:
            msg = ("No clusters are currently configured. "
                   "To configure one, run `dcos cluster setup <dcos_url>`")
        raise DCOSException(msg)
    else:
        emitter.publish(clusters_table(clusters))

    return


def _remove(name=None, all_clusters=False):
    """
    :param name: name of cluster
    :type name: str
    :param all_clusters: remove all clusters if True
    :type all_clusters: bool
    :rtype: None
    """
    if all_clusters:
        for c in cluster.get_clusters():
            cluster.remove(c.get_name())
    else:
        cluster.remove(name)


def _attach(name):
    """
    :param name: name of cluster
    :type name: str
    :rtype: None
    """

    c = cluster.get_cluster(name)
    if c is not None:
        return cluster.set_attached(c.get_cluster_path())
    else:
        raise DCOSException("Cluster [{}] does not exist".format(name))


def _rename(name, new_name):
    """
    :param name: name of cluster
    :type name: str
    :param new_name: new_name of cluster
    :type new_name: str
    :rtype: None
    """

    c = cluster.get_cluster(name)
    other = cluster.get_cluster(new_name)
    if c is None:
        raise DCOSException("Cluster [{}] does not exist".format(name))
    elif other and other != c:
        msg = "A cluster with name [{}] already exists"
        raise DCOSException(msg.format(new_name))
    else:
        config.set_val("cluster.name", new_name, c.get_config_path())


def setup(dcos_url,
          insecure=False, no_check=False, ca_certs=None,
          password_str=None, password_env=None, password_file=None,
          provider=None, username=None, key_path=None):
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

        # Make sure to ignore any environment variable for the DCOS URL.
        # There is already a mandatory command argument for this.
        env_warning = ("Ignoring '{}' environment variable.\n")
        if "DCOS_URL" in os.environ:
            emitter.publish(DefaultError(env_warning.format('DCOS_URL')))
            del os.environ["DCOS_URL"]
        if "DCOS_DCOS_URL" in os.environ:
            emitter.publish(DefaultError(env_warning.format('DCOS_DCOS_URL')))
            del os.environ["DCOS_DCOS_URL"]

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
        elif _needs_cluster_cert(dcos_url):
            cert = cluster.get_cluster_cert(dcos_url)
            if cert:
                stored_cert = _store_cluster_cert(cert, no_check)
            else:
                config.set_val("core.ssl_verify", "false")
        else:
            config.set_val("core.ssl_verify", "false")

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

    if not no_check and not _user_cert_validation(cert):
        raise DCOSException("Couldn't get confirmation for the fingerprint.")

    with util.temptext() as temp_file:
        _, temp_path = temp_file

        with open(temp_path, 'w') as f:
            f.write(cert)

        cert_path = os.path.join(
            config.get_attached_cluster_path(), "dcos_ca.crt")

        util.sh_copy(temp_path, cert_path)

    config.set_val("core.ssl_verify", cert_path)
    return True


def _needs_cluster_cert(dcos_url):
    """Checks whether the certificate bundle from the cluster should
    be downloaded (when dcos_url uses HTTPS). This is done by making a request
    to the cluster, it might work out of the box (when we're dealing with a
    load-balancer or when a custom CA has already been added to the system).

    :param dcos_url: URL of the DC/OS cluster
    :type dcos_url: str
    :returns: whether or not to download the cert bundle
    :rtype: bool
    """

    if dcos_url.startswith('https://'):
        try:
            requests.get(dcos_url, timeout=http.DEFAULT_TIMEOUT)
        except requests.exceptions.SSLError:
            return True
        except Exception as e:
            logger.warning(
                'Unexpected exception occurred while calling %s: %s',
                dcos_url, e)
            return True

    return False
