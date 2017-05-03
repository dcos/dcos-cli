import os

import docopt

import dcoscli
from dcos import auth, cmds, config, emitting, http, util
from dcos.errors import DCOSException, DefaultError
from dcoscli import tables
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
            hierarchy=['auth', 'list-providers'],
            arg_keys=['--json'],
            function=_list_providers),

        cmds.Command(
            hierarchy=['auth', 'login'],
            arg_keys=['--password', '--password-env', '--password-file',
                      '--provider', '--username', '--private-key'],
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


def _list_providers(json_):
    """
    :returns: providers available for configured cluster
    :rtype: dict
    """

    providers = auth.get_providers()
    if providers or json_:
        emitting.publish_table(
            emitter, providers, tables.auth_provider_table, json_)
    else:
        raise DCOSException("No providers configured for your cluster")


def _get_password(password_str, password_env, password_file):
    """
    Get password for authentication

    :param password_str: password
    :type password_str: str
    :param password_env: name of environment variable with password
    :type password_env: str
    :param password_file: path to file with password
    :type password_file: bool
    :returns: password or None if no password specified
    :rtype: str | None
    """

    password = None
    if password_str:
        password = password_str
    elif password_env:
        password = os.environ.get(password_env)
        if password is None:
            msg = "Environment variable specified [{}] does not exist"
            raise DCOSException(msg.format(password_env))
    elif password_file:
        password = util.read_file_secure(password_file)
    return password


def _login(password_str, password_env, password_file,
           provider, username, key_path):
    """
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
    :rtype: int
    """

    dcos_url = config.get_config_val("core.dcos_url")
    if dcos_url is None:
        msg = ("Please provide the url to your DC/OS cluster: "
               "`dcos config set core.dcos_url`")
        raise DCOSException(msg)

    # every call to login will generate a new token if applicable
    _logout()

    login(dcos_url, password_str, password_env, password_file,
          provider, username, key_path)

    emitter.publish("Login successful!")
    return 0


def _trigger_client_method(
        provider, provider_info, username=None, password=None, key_path=None):
    """
    Trigger client method for authentication type user requested

    :param provider: provider_id requested by user
    :type provider: str
    :param provider_info: info about auth type defined by provider
    :param provider_info: dict
    :param username: username
    :type username: str
    :param password: password
    :type password: str
    :param key_path: path to file with service key
    :type param: str
    :rtype: None
    """

    client_method = provider_info.get("client-method")
    dcos_url = config.get_config_val("core.dcos_url")

    if client_method == "browser-prompt-authtoken":
        auth.browser_prompt_auth(dcos_url, provider_info)
    elif client_method == "browser-prompt-oidcidtoken-get-authtoken":
        auth.oidc_implicit_flow_auth(dcos_url)
    elif client_method == "dcos-usercredential-post-receive-authtoken" or \
            client_method == "dcos-credential-post-receive-authtoken":
        if not username or not password:
            msg = "Please specify username and password for provider [{}]"
            raise DCOSException(msg.format(provider))
        auth.dcos_uid_password_auth(dcos_url, username, password)
    elif client_method == "dcos-servicecredential-post-receive-authtoken":
        if not username or not key_path:
            msg = "Please specify username and service key for provider [{}]"
            raise DCOSException(msg.format(provider))
        auth.servicecred_auth(dcos_url, username, key_path)
    else:
        msg = "Authentication by provider [{}] is not supported by this CLI"
        raise DCOSException(msg.format(provider))


def _logout():
    """
    Logout the user from dcos acs auth or oauth

    :returns: process status
    :rtype: int
    """

    if config.get_config_val("core.dcos_acs_token") is not None:
        config.unset("core.dcos_acs_token")
    return 0


def login(dcos_url, password_str, password_env, password_file,
          provider, username, key_path):
    """
    :param dcos_url: URL of DC/OS cluster
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
    :rtype: int
    """

    password = _get_password(password_str, password_env, password_file)
    if provider is None:
        if username and password:
            auth.dcos_uid_password_auth(dcos_url, username, password)
        elif username and key_path:
            auth.servicecred_auth(dcos_url, username, key_path)
        else:
            try:
                providers = auth.get_providers()
                # Let users know if they have non-default providers configured
                # This is a weak check, we should check default versions per
                # DC/OS version since defaults will change. jj
                if len(providers) > 2:
                    msg = ("\nYour cluster has several authentication "
                           "providers enabled. Run `dcos auth "
                           "list-providers` to see all providers and `dcos "
                           "auth login --provider <provider-id>` to "
                           "authenticate with a specific provider\n")
                    emitter.publish(DefaultError(msg))
            except DCOSException:
                pass
            finally:
                auth.header_challenge_auth(dcos_url)
    else:
        providers = auth.get_providers()
        if providers.get(provider):
            _trigger_client_method(
                provider, providers[provider], username, password, key_path)
        else:
            msg = "Provider [{}] not configured on your cluster"
            raise DCOSException(msg.format(provider))

    return 0
