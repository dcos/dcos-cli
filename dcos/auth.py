import json
import sys
import uuid

import pkg_resources
from dcos import config, emitting, errors, http, jsonitem, util
from dcos.errors import DCOSException
from six import iteritems

from oauth2client import client

CLIENT_ID = '6a552732-ab9b-410d-9b7d-d8c6523b09a1'
CLIENT_SECRET = 'f56c1e2b-8599-40ca-b6a0-3aba3e702eae'
AUTH_URL = 'https://accounts.mesosphere.com/oauth/authorize'
TOKEN_URL = 'https://accounts.mesosphere.com/oauth/token'
USER_INFO_URL = 'https://accounts.mesosphere.com/api/v1/user.json'
CORE_TOKEN_KEY = 'token'
CORE_EMAIL_KEY = 'email'
emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


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

    toml_config = util.get_config(True)

    section = 'core'
    config_schema = json.loads(
        pkg_resources.resource_string(
            'dcoscli',
            'data/config-schema/core.json').decode('utf-8'))
    for k, v in iteritems(key_dict):
        python_value = jsonitem.parse_json_value(k, v, config_schema)
        name = '{}.{}'.format(section, k)
        toml_config[name] = python_value

    config.save(toml_config)
    return None
