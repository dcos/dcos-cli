import json
import sys
import uuid

import dcoscli
import docopt
import rollbar
import six
from dcos import http, util
from dcoscli.constants import (ROLLBAR_SERVER_POST_KEY,
                               SEGMENT_IO_CLI_ERROR_EVENT,
                               SEGMENT_IO_CLI_EVENT, SEGMENT_IO_WRITE_KEY_PROD,
                               SEGMENT_URL)
from dcoscli.subcommand import default_doc
from requests.auth import HTTPBasicAuth

logger = util.get_logger(__name__)
session_id = uuid.uuid4().hex


def _track(conf):
    """
    Whether or not to send reporting information

    :param conf: dcos config file
    :type conf: Toml
    :returns: whether to send reporting information
    :rtype: bool
    """

    return dcoscli.version != 'SNAPSHOT' and conf.get('core.reporting', True)


def _segment_track(event, conf, properties):
    """
    Send a segment.io 'track' event

    :param event: name of event
    :type event: string
    :param conf: dcos config file
    :type conf: Toml
    :param properties: event properties
    :type properties: dict
    :rtype: None
    """

    data = {'event': event,
            'properties': properties,
            'anonymousId': session_id}

    _segment_request('track', data)


def _segment_request(path, data):
    """
    Send a segment.io HTTP request

    :param path: URL path
    :type path: str
    :param data: json POST data
    :type data: dict
    :rtype: None
    """

    key = SEGMENT_IO_WRITE_KEY_PROD

    try:
        # Set both the connect timeout and the request timeout to 1s,
        # to prevent rollbar from hanging the CLI commands
        http.post('{}/{}'.format(SEGMENT_URL, path),
                  json=data,
                  auth=HTTPBasicAuth(key, ''),
                  timeout=(1, 1))
    except Exception as e:
        logger.exception(e)


def track_err(pool, exit_code, err, conf, cluster_id):
    """
    Report error details to analytics services.

    :param pool: thread pool
    :type pool: ThreadPoolExecutor
    :param exit_code: exit code of tracked process
    :type exit_code: int
    :param err: stderr of tracked process
    :type err: str
    :param conf: dcos config file
    :type conf: Toml
    :param cluster_id: dcos cluster id to send to segment
    :type cluster_id: str
    :rtype: None
    """

    if not _track(conf):
        return

    # Segment.io calls are async, but rollbar is not, so for
    # parallelism, we must call segment first.
    _segment_track_err(pool, conf, cluster_id, err, exit_code)
    _rollbar_track_err(conf, cluster_id, err, exit_code)


def segment_track_cli(pool, conf, cluster_id):
    """
    Send segment.io cli event.

    :param pool: thread pool
    :type pool: ThreadPoolExecutor
    :param conf: dcos config file
    :type conf: Toml
    :param cluster_id: dcos cluster id to send to segment
    :type cluster_id: str
    :rtype: None
    """

    if not _track(conf):
        return

    props = _base_properties(conf, cluster_id)
    pool.submit(_segment_track, SEGMENT_IO_CLI_EVENT, conf, props)


def _segment_track_err(pool, conf, cluster_id, err, exit_code):
    """
    Send segment.io error event.

    :param pool: thread pool
    :type segment: ThreadPoolExecutor
    :param conf: dcos config file
    :type conf: Toml
    :param cluster_id: dcos cluster id to send to segment
    :type cluster_id: str
    :param err: stderr of tracked process
    :type err: str
    :param exit_code: exit code of tracked process
    :type exit_code: int
    :rtype: None
    """

    props = _base_properties(conf, cluster_id)
    props['err'] = err
    props['exit_code'] = exit_code
    pool.submit(_segment_track, SEGMENT_IO_CLI_ERROR_EVENT, conf, props)


def _rollbar_track_err(conf, cluster_id, err, exit_code):
    """
    Report to rollbar.  Synchronous.

    :param conf: dcos config file
    :type conf: Toml
    :param cluster_id: dcos cluster id to send to segment
    :type cluster_id: str
    :param err: stderr of tracked process
    :type err: str
    :param exit_code: exit code of tracked process
    :type exit_code: int
    :rtype: None
    """

    rollbar.init(ROLLBAR_SERVER_POST_KEY, 'prod')

    props = _base_properties(conf, cluster_id)
    props['exit_code'] = exit_code

    lines = err.split('\n')
    if len(lines) >= 2:
        title = lines[-2]
    else:
        title = err
    props['stderr'] = err

    try:
        rollbar.report_message(title, 'error', extra_data=props)
    except Exception as e:
        logger.exception(e)


def _command():
    """ Return the subcommand used in this dcos process.

    :returns: subcommand used in this dcos process
    :rtype: str
    """

    args = docopt.docopt(default_doc("dcos"),
                         help=False,
                         options_first=True)
    return args.get('<command>', "") or ""


def _base_properties(conf=None, cluster_id=None):
    """
    These properties are sent with every analytics event.

    :param conf: dcos config file
    :type conf: Toml
    :param cluster_id: dcos cluster id to send to segment
    :type cluster_id: str
    :rtype: dict
    """

    if not conf:
        conf = util.get_config()

    if len(sys.argv) > 1:
        cmd = 'dcos ' + _command()
        full_cmd = 'dcos ' + ' '.join(sys.argv[1:])
    else:
        cmd = 'dcos'
        full_cmd = 'dcos'

    try:
        dcos_hostname = six.moves.urllib.parse.urlparse(
            conf.get('core.dcos_url')).hostname
    except:
        logger.exception('Unable to find the hostname of the cluster.')
        dcos_hostname = None

    conf = [prop for prop in list(conf.property_items())
            if prop[0] != "core.dcos_acs_token"]

    return {
        'cmd': cmd,
        'full_cmd': full_cmd,
        'dcoscli.version': dcoscli.version,
        'python_version': str(sys.version_info),
        'config': json.dumps(conf),
        'DCOS_HOSTNAME': dcos_hostname,
        'CLUSTER_ID': cluster_id
    }
