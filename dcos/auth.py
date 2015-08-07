import json
import os
import sys
import uuid

import pkg_resources
import toml
from dcos import config, constants, emitting, errors, http, jsonitem, util
from dcos.errors import DCOSException
from six import iteritems

from oauth2client import client

AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'
USER_INFO_URL = 'https://www.googleapis.com/plus/v1/people/me'
CORE_TOKEN_KEY = 'token'
CORE_EMAIL_KEY = 'email'
emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def _authorize():
    """Create OAuth flow and authorize user

    :return: credentials dict
    :rtype: dict
    """

    auth2_client_id, auth2_client_secret = _get_auth2_secrets()
    try:
        flow = client.OAuth2WebServerFlow(
            client_id=auth2_client_id,
            client_secret=auth2_client_secret,
            scope='email profile',
            auth_uri=AUTH_URL,
            token_uri=TOKEN_URL,
            redirect_uri=client.OOB_CALLBACK_URN,
            response_type='code'
        )
        return _run(flow)
    except:
        logger.exception('Error during OAuth web flow')
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
    mail = data.get('emails', '')[0].get('value', '')
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

    emitter.publish(
        errors.DefaultError(
            '\n\n\n{}\n\n    {}\n\n'.format(
                'Go to the following link in your browser:',
                flow.step1_get_authorize_url())))

    sys.stderr.write('Enter verification code: ')
    code = sys.stdin.readline().strip()
    if not code:
        sys.stderr.write('Skipping authentication.\nEnter email address: ')

        email = sys.stdin.readline().strip()
        if not email:
            emitter.publish(
                errors.DefaultError(
                    'Skipping email input.'))
            email = str(uuid.uuid1())

        return {CORE_EMAIL_KEY: email}

    return make_oauth_request(code, flow)


def check_if_user_authenticated():
    """Check if user is authenticated already

    :returns user auth status
    :rtype: boolean
    """

    dcos_config = util.get_config()
    return dcos_config.get('core.email', '') != ''


def force_auth():
    """Make user authentication process

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
    with util.open_file(config_path, 'w') as config_file:
        config_file.write(serial)

    return None


def _get_auth2_secrets():
    """Returns list of OAuth2 secrets from configuration

    :returns values: core.client_id, core.client_secret
    :rtype: list
    """

    config = util.get_config()

    auth2_secrets = [util.get_config_vals(['core.client_id'], config)[0],
                     util.get_config_vals(['core.client_secret'], config)[0]]
    for value in auth2_secrets:
        if value == None:
            raise DCOSException('There were no OAuth2 secrets configured.')
    return auth2_secrets
