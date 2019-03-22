import os

from dcos import config, constants, mesos
from dcos.errors import DCOSException
from dcos.util import get_logger


logger = get_logger(__name__)


def get_ssh_user(ssh_config_file, user):
    """Returns the SSH user name to use accessing cluster nodes. If an ssh
    config file provided, expects the username to be specified in the
    file and ignores any provided username. Username resolution
    follows this logic, use any username explicitly provided, else use
    the one in dcos cli config, else use default ssh user from constants.

    :param ssh_config_file: SSH options
    :type ssh_config_file: [str]
    :param user: SSH user
    :type user: str | None
    :rtype: str | None

    """

    if ssh_config_file:
        return None

    if user:
        return user

    dcos_config_ssh_user = config.get_config_val("core.ssh_user")
    if dcos_config_ssh_user:
        return dcos_config_ssh_user

    return constants.DEFAULT_SSH_USER


def get_ssh_user_options(ssh_config_file, user):
    """Returns the SSH user arguments for the given parameters.

    :param ssh_config_file: SSH config file.
    :type ssh_config_file: str | None
    :param user: SSH user
    :type user: str | None
    :rtype: str

    """

    user = get_ssh_user(ssh_config_file, user)
    if not user:
        return ''

    return '-l {}'.format(user)


def get_ssh_proxy_options(ssh_options, user_options='',
                          proxy_ip=None, master_proxy=False):
    """Returns the SSH proxy arguments for the given parameters.

    :param ssh_options: SSH options
    :type ssh_options: str
    :param user_option: SSH user option string
    :type user_option: str
    :param proxy_ip: SSH proxy node
    :type proxy_ip: str | None
    :param master_proxy: Use master nodes as proxy
    :type master_proxy: boolean
    :rtype: str

    """

    if not proxy_ip:
        dcos_config_proxy_ip = config.get_config_val("core.ssh_proxy_ip")
        if dcos_config_proxy_ip:
            proxy_ip = dcos_config_proxy_ip
        elif master_proxy:
            dcos_client = mesos.DCOSClient()
            master_public_ip = dcos_client.metadata().get('PUBLIC_IPV4')
            if not master_public_ip:
                raise DCOSException(("Cannot use --master-proxy.  Failed to "
                                     "find 'PUBLIC_IPV4' at {}").format(
                                         dcos_client.get_dcos_url('metadata')))
            proxy_ip = master_public_ip

    if not proxy_ip:
        return ''

    if proxy_ip and not os.environ.get('SSH_AUTH_SOCK') and not ssh_options:
        raise DCOSException(
            "There is no SSH_AUTH_SOCK env variable, which likely means "
            "you aren't running `ssh-agent`.  `dcos node ssh "
            "--master-proxy/--proxy-ip` depends on `ssh-agent` to safely "
            "use your private key to hop between nodes in your cluster.  "
            "Please run `ssh-agent`, then add your private key with "
            "`ssh-add`.")

    proxy_options = '-A -t {0} {1} {2} -- \"ssh'.format(
        ssh_options, user_options, proxy_ip)
    return proxy_options


def get_ssh_options(config_file, options=[], user=None,
                    proxy_ip=None, master_proxy=False):
    """Returns the SSH arguments for the given parameters.  Used by
    commands that wrap SSH.

    :param config_file: SSH config file.
    :type config_file: str | None
    :param options: SSH options
    :type options: [str]
    :param user: SSH user
    :type user: str | None
    :param proxy_ip: SSH proxy node
    :type proxy_ip: str | None
    :param master_proxy: Use master nodes as proxy
    :type master_proxy: boolean
    :rtype: str
    """

    ssh_options = ' '.join('-o {}'.format(opt) for opt in options)

    if config_file:
        ssh_options += ' -F {}'.format(config_file)

    user_options = get_ssh_user_options(config_file, user)
    proxy_options = get_ssh_proxy_options(
        ssh_options, user_options, proxy_ip, master_proxy)
    ssh_options = "{0} -A -t {1} {2}".format(
        proxy_options, ssh_options, user_options)

    return ssh_options
