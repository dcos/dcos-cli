import json
import os
import socket
import urllib

from concurrent import futures
from urllib.parse import urlparse

import docopt
import requests

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

import dcoscli

from dcos import auth, cluster, cmds, config, emitting, http, jsonitem, util
from dcos.errors import (DCOSAuthenticationException, DCOSException,
                         DCOSHTTPException, DefaultError)
from dcoscli.auth.main import login
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.tables import clusters_table
from dcoscli.util import confirm, decorate_docopt_usage, prompt_with_choices

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
    doc_name = 'cluster'

    # If a cluster is attached and the cluster linker API is reachable,
    # use cluster_ee.txt.
    dcos_url = config.get_config_val('core.dcos_url')
    if dcos_url:
        try:
            cluster.get_cluster_links(dcos_url)
            doc_name = 'cluster_ee'
        except Exception:
            pass

    args = docopt.docopt(
        default_doc(doc_name),
        argv=argv,
        version='dcos-cluster version {}'.format(dcoscli.version))

    http.silence_requests_warnings()

    return cmds.execute(_cmds(doc_name), args)


def _cmds(doc_name):
    """
    :param doc_name: the docopt help file in use
    :type doc_name: str
    :returns: all the supported commands
    :rtype: list of dcos.cmds.Command
    """

    list_arg_keys = ['--json', '--attached']
    if doc_name == 'cluster_ee':
        list_arg_keys.append('--linked')

    commands = [
        cmds.Command(
            hierarchy=['cluster', 'setup'],
            arg_keys=['<dcos_url>',
                      '--insecure', '--no-check', '--ca-certs',
                      '--password', '--password-env', '--password-file',
                      '--provider', '--username', '--private-key'],
            function=setup),

        cmds.Command(
            hierarchy=['cluster', 'list'],
            arg_keys=list_arg_keys,
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
    ]

    if doc_name == 'cluster_ee':
        commands.append(cmds.Command(
            hierarchy=['cluster', 'link'],
            arg_keys=['<dcos_url>', '--provider'],
            function=_link))
        commands.append(cmds.Command(
            hierarchy=['cluster', 'unlink'],
            arg_keys=['<name>'],
            function=_unlink))

    # This needs to be last as it's also a fallback.
    commands.append(cmds.Command(
        hierarchy=['cluster'],
        arg_keys=['--info'],
        function=_info))

    return commands


def _info(info):
    """
    :param info: Whether to output a description of this subcommand
    :type info: boolean
    :returns: process status
    :rtype: int
    """

    emitter.publish(default_command_info("cluster"))
    return 0


def _list(json_, attached, linked=False):
    """
    List configured clusters.

    :param json_: output json if True
    :type json_: bool
    :param attached: return only attached cluster
    :type attached: bool
    :param linked: return only linked clusters
    :type linked: bool
    :rtype: None
    """

    if attached:
        clusters = [c.dict() for c in cluster.get_clusters()
                    if c.is_attached()]
    else:
        if linked:
            clusters = cluster.get_linked_clusters()
        else:
            clusters = cluster.get_clusters(True)

        if clusters:
            # Query for cluster versions concurrently.
            nb_workers = len(clusters)
            with futures.ThreadPoolExecutor(max_workers=nb_workers) as pool:
                reqs = [pool.submit(c.dict) for c in clusters]
                clusters = [r.result() for r in futures.as_completed(reqs)]

    if json_:
        emitter.publish(clusters)
    elif len(clusters) == 0:
        if attached:
            msg = ("No cluster is attached. "
                   "Please run `dcos cluster attach <cluster-name>")
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
            cluster.remove(c.get_cluster_id())
    else:
        cluster.remove(name)


def _attach(name):
    """
    :param name: name of cluster
    :type name: str
    :rtype: None
    """

    c = cluster.get_cluster(name)
    if not c:
        raise DCOSException("Cluster [{}] does not exist".format(name))

    if c.get_status() == cluster.STATUS_UNCONFIGURED:
        return setup(c.get_url(), provider=c.get_provider().get('id'))

    return cluster.set_attached(c.get_cluster_path())


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


def _link(dcos_url, provider_id):
    """
    Link a DC/OS cluster to the current one.

    :param dcos_url: master ip of the cluster to link to
    :type dcos_url: str
    :param provider_id: login provider ID for the linked cluster
    :type provider_id: str
    :returns: process status
    :rtype: int
    """

    current_cluster = cluster.get_attached_cluster()
    if not current_cluster:
        raise DCOSException('No cluster is attached, cannot link.')
    current_cluster_url = current_cluster.get_url()

    # Accept the same formats as the `setup` command
    # eg. "my-cluster.example.com" -> "https://my-cluster.example.com"
    dcos_url = jsonitem._parse_url(dcos_url)

    try:
        linked_cluster_ip = socket.gethostbyname(urlparse(dcos_url).netloc)
    except OSError as error:
        raise DCOSException("Unable to retrieve IP for '{dcos_url}': {error}"
                            .format(dcos_url=dcos_url, error=error))

    # Make sure the linked cluster is already configured (based on its IP)
    for configured_cluster in cluster.get_clusters():
        configured_cluster_host = \
            urlparse(configured_cluster.get_url()).netloc

        try:
            configured_cluster_ip = \
                socket.gethostbyname(configured_cluster_host)
        except OSError as error:
            continue

        if linked_cluster_ip == configured_cluster_ip:
            linked_cluster_id = configured_cluster.get_cluster_id()
            linked_cluster_name = configured_cluster.get_name()
            break
    else:
        msg = ("The cluster you are linking to must be set up locally before\n"
               "running the `cluster link` command. To set it up now, run:\n"
               "    $ dcos cluster setup {}".format(dcos_url))
        raise DCOSException(msg)

    if linked_cluster_id == current_cluster.get_cluster_id():
        raise DCOSException('Cannot link a cluster to itself.')

    providers = auth.get_providers(dcos_url)

    if provider_id:
        if provider_id not in providers:
            raise DCOSException(
                "Incorrect provider ID '{}'.".format(provider_id))
        provider_type = providers[provider_id]['authentication-type']
    else:
        (provider_id, provider_type) = _prompt_for_login_provider(providers)

    message = {
        'id': linked_cluster_id,
        'name': linked_cluster_name,
        'url': dcos_url,
        'login_provider': {
            'id': provider_id,
            'type': provider_type}}

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'}

    try:
        http.post(
            urllib.parse.urljoin(current_cluster_url, '/cluster/v1/links'),
            data=json.dumps(message),
            headers=headers)
    except DCOSHTTPException as e:
        if e.status() == 409:
            raise DCOSException("This cluster link already exists.")
        raise

    return 0


def _unlink(name):
    """
    Unlink a DC/OS cluster.

    :param name: ID or name of the cluster
    :type name: str
    :returns: process status
    :rtype: int
    """

    c = cluster.get_cluster(name)
    if c:
        name = c.get_cluster_id()

    dcos_url = config.get_config_val('core.dcos_url')
    endpoint = urllib.parse.urljoin(
            dcos_url, '/cluster/v1/links/' + name)

    try:
        http.delete(endpoint)
    except DCOSHTTPException as e:
        if e.status() == 404:
            raise DCOSException('Unknown cluster link {}.'.format(name))
        raise

    return 0


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


def _prompt_for_login_provider(providers):
    """Prompt the user with login providers.

    :param providers: Login providers from "/acs/api/v1/auth/providers"
    :type providers: dict
    :returns: (provider_id, provider_type)
    :rtype: (string, string)
    """

    choices = []
    descriptions = []
    for idx in sorted(providers.keys()):
        provider_type = providers[idx].get('authentication-type')
        if provider_type not in [
                auth.AUTH_TYPE_DCOS_UID_PASSWORD,
                auth.AUTH_TYPE_DCOS_UID_PASSWORD_LDAP,
                auth.AUTH_TYPE_SAML_SP_INITIATED,
                auth.AUTH_TYPE_OIDC_AUTHORIZATION_CODE_FLOW]:
            continue

        choices.append(idx)
        description = auth.auth_type_description(providers[idx])
        descriptions.append(description)

    if not choices:
        raise DCOSException(
            "There is no supported login provider on the linked cluster.")
    elif len(choices) == 1:
        # There is only one supported login provider, don't prompt.
        provider_id = choices[0]
        return (provider_id, providers[provider_id]['authentication-type'])

    # Prompt user to choose a provider ID.
    msg = ("Choose the login method and provider to enable switching to this "
           "linked cluster:")
    provider_id = prompt_with_choices(choices, descriptions, msg)
    if not provider_id:
        raise DCOSException("Incorrect login provider.")

    return (provider_id, providers[provider_id]['authentication-type'])
