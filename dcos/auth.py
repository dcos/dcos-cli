import json
import os
import uuid

import pkg_resources
import toml
from dcos import config, constants, emitting, errors, http, jsonitem, util
from dcos.errors import DCOSException
from six import iteritems, moves

from oauth2client import client

CLIENT_ID = '6a552732-ab9b-410d-9b7d-d8c6523b09a1'
CLIENT_SECRET = 'f56c1e2b-8599-40ca-b6a0-3aba3e702eae'
AUTH_URL = 'https://accounts.mesosphere.com/oauth/authorize'
TOKEN_URL = 'https://accounts.mesosphere.com/oauth/token'
USER_INFO_URL = 'https://accounts.mesosphere.com/api/v1/user.json'
CORE_TOKEN_KEY = 'token'
CORE_EMAIL_KEY = 'email'
emitter = emitting.FlatEmitter()


def _authorize():
    """Create OAuth flow and authorize user

    :return: credentials dict
    :rtype: dict
    """
    try:
        flow = client.OAuth2WebServerFlow(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope='',
            auth_uri=AUTH_URL,
            token_uri=TOKEN_URL,
            redirect_uri=client.OOB_CALLBACK_URN,
            response_type='code'
        )
        return _run(flow)
    except:
        raise DCOSException('There was a problem with '
                            'web authentication.')


def make_oauth_request(code, flow):
    """Make request to auth server using auth_code.

    :param: code: auth_code read from cli
    :param: flow: OAuth2 web server flow
    :return: dict with the keys token and email
    :rtype: dict
    """
    credential = flow.step2_exchange(code)
    token = credential.access_token
    headers = {'Authorization': str('Bearer ' + token)}
    data = http.requests.get(USER_INFO_URL, headers=headers).json()
    mail = data['email']
    credentials = {CORE_TOKEN_KEY: credential.access_token,
                   CORE_EMAIL_KEY: mail}
    return credentials


def _run(flow):
    """Make authorization and retrieve access token and user email.

    :param flow: OAuth2 web server flow
    :param launch_browser: if possible to run browser
    :return: dict with the keys token and email
    :rtype: dict
    """

    auth_url = flow.step1_get_authorize_url()
    message = """Thank you for installing the Mesosphere DCOS CLI.
Please log in with your Mesosphere Account by pasting
the following URL into your browser to continue."""
    emitter.publish(errors.DefaultError(
        '{message}\n\n    {url}\n\n'.format(message=message,
                                            url=auth_url,)))

    code = moves.input('Please enter Mesosphere verification code: ').strip()
    if not code:
        email = moves.input('Skipping authentication.'
                            ' Please enter email address:').strip()
        if not email:
            emitter.publish(errors.DefaultError('Skipping email input,'
                                                ' using anonymous id:'))
            email = str(uuid.uuid1())
        return {CORE_EMAIL_KEY: email}

    return make_oauth_request(code, flow)


def check_if_user_authenticated():
    """ check if user is authenticated already

    :returns user auth status
    :rtype: boolean
    """

    dcos_config = util.get_config()
    return dcos_config.get('core.email', '') != ''


def force_auth():
    """ Make user authentication process

    :returns authentication process status
    :rtype: boolean
    """

    credentials = _authorize()
    _save_auth_keys(credentials)


def _save_auth_keys(key_dict):
    """
    :param key_dict: auth parameters dict
    :type key_dict: dict
    :rtype: None
    """

    config_path = os.environ[constants.DCOS_CONFIG_ENV]
    toml_config = config.mutable_load_from_path(config_path)

    section = 'core'
    config_schema = json.loads(
        pkg_resources.resource_string(
            'dcoscli',
            'data/config-schema/core.json').decode('utf-8'))
    for k, v in iteritems(key_dict):
        python_value = jsonitem.parse_json_value(k, v, config_schema)
        name = '{}.{}'.format(section, k)
        toml_config[name] = python_value

    serial = toml.dumps(toml_config._dictionary)
    with open(config_path, 'w') as config_file:
        config_file.write(serial)

    return None
