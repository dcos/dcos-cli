import docopt
from six.moves import urllib

import dcoscli
from dcos import cmds, config, emitting, http, util
from dcos.errors import DCOSAuthorizationException, DCOSException
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
            arg_keys=[],
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


def _login():
    """
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

    # hit protected endpoint which will prompt for auth if cluster has auth
    try:
        url = urllib.parse.urljoin(dcos_url, 'exhibitor/')
        http.get(url)
    # if the user is authenticated, they have effectively "logged in" even if
    # they are not authorized for this endpoint
    except DCOSAuthorizationException:
        pass

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
