import os
import shutil

import dcoscli
import docopt
from dcos import cmds, config, constants, emitting, http, util
from dcos.errors import (DCOSAuthorizationException, DCOSException,
                         DCOSExceptionSSL)
from dcoscli.package.main import confirm
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage
from OpenSSL.crypto import FILETYPE_PEM, load_certificate

from six.moves import urllib

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
        default_doc("auth"),
        argv=argv,
        version='dcos-auth version {}'.format(dcoscli.version))

    http.silence_requests_warnings()

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: all the supported commands
    :rtype: list of dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['auth', 'login'],
            arg_keys=['--yes'],
            function=_login),

        cmds.Command(
            hierarchy=['auth', 'logout'],
            arg_keys=[],
            function=_logout),

        cmds.Command(
            hierarchy=['auth'],
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

    emitter.publish(default_command_info("auth"))
    return 0


def _verify_cert(cert, yes):
    """
    User verification of cert

    :param cert:
    :returns: verification of cert
    :rtype: bool
    """

    pem_cert = load_certificate(FILETYPE_PEM, cert)
    fingerprint = pem_cert.digest("sha1")
    msg = ("Correct sha1 fingerprint of cluster certificate?: "
           "{}".format(fingerprint.decode('utf-8')))
    return confirm(msg, yes=yes)


def _add_cluster_cert(dcos_url, yes):
    """
    If the user allows, download the cluster CA and set `core.dcos_url`
    to the path of the downloaded CA

    :param dcos_url: cluster url
    :type dcos_url: str
    :param yes: whether or not to prompt user for confirmation
    :type yes: bool
    :returns: whether or not successfully added cert
    :rtype: bool
    """

    msg = "An SSL error occured. Download the cluster CA cert?"
    if not confirm(msg, yes=yes):
        return False

    with util.temptext() as file_tmp:
        _, cert_tmp = file_tmp
        ca_cert_url = urllib.parse.urljoin(dcos_url, "ca/api/v2/info")

        with open(cert_tmp, 'wb') as f:
            r = http.post(ca_cert_url, verify=False, json={})
            cert = r.json()["result"].get("certificate").encode('utf-8')
            if _verify_cert(cert, yes):
                f.write(cert)
            else:
                return False

            # store the cert in DCOS_DIR
            dcos_dir = os.path.expanduser(
                os.path.join("~", constants.DCOS_DIR))
            util.ensure_dir_exists(dcos_dir)
            cert_path = os.path.join(dcos_dir, "dcos-ca.pem")
            shutil.move(cert_tmp, cert_path)
            # add cert to config
            config.set_val("core.ssl_verify", cert_path)
            return True


def _prompt_for_auth(dcos_url):
    """
    hit protected endpoint which will prompt for auth if cluster has auth

    :param dcos_url: cluster url
    :type dcos_url: str
    :rtype: None
    """

    try:
        url = urllib.parse.urljoin(dcos_url, 'exhibitor/')
        http.get(url)
    # if the user is authenticated, they have effectively "logged in" even if
    # they are not authorized for this endpoint
    except DCOSAuthorizationException:
        pass


def _login(yes):
    """
    :param yes: Whether to prompt for verfication of CA certificate
    :type yes: boolean
    :returns: process status
    :rtype: int
    """

    # every call to login will generate a new token if applicable
    _logout()
    dcos_url = config.get_config_val("core.dcos_url")
    if dcos_url is None:
        msg = ("Please provide the url to your DC/OS cluster: "
               "`dcos config set core.dcos_url`")
        raise DCOSException(msg)

    try:
        _prompt_for_auth(dcos_url)
    except DCOSExceptionSSL:
        verify = config.get_config_val("core.ssl_verify")
        if verify is None and _add_cluster_cert(dcos_url, yes) is True:
            # retry login with new certificate
            _prompt_for_auth(dcos_url)
        else:
            raise DCOSExceptionSSL()

    emitter.publish("Login successful!")
    return 0


def _logout():
    """
    Logout the user from dcos acs auth or oauth

    :returns: process status
    :rtype: int
    """

    if config.get_config_val("core.dcos_acs_token") is not None:
        config.unset("core.dcos_acs_token")
    return 0
