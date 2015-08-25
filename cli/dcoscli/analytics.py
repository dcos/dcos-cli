import json
import sys
import uuid

import dcoscli
import docopt
import rollbar
import six
from concurrent.futures import ThreadPoolExecutor
from dcos import http, util
from dcoscli.constants import (ROLLBAR_SERVER_POST_KEY,
                               SEGMENT_IO_CLI_ERROR_EVENT,
                               SEGMENT_IO_CLI_EVENT, SEGMENT_IO_WRITE_KEY_PROD,
                               SEGMENT_URL)
from requests.auth import HTTPBasicAuth

logger = util.get_logger(__name__)
session_id = uuid.uuid4().hex


def wait_and_track(subproc):
    """
    Run a command and report it to analytics services.

    :param subproc: Subprocess to capture
    :type subproc: Popen
    :returns: exit code of subproc
    :rtype: int
    """

    rollbar.init(ROLLBAR_SERVER_POST_KEY, 'prod')

    conf = util.get_config()
    report = conf.get('core.reporting', True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        if report:
            _segment_track_cli(pool, conf)

        exit_code, err = wait_and_capture(subproc)

        # We only want to catch exceptions, not other stderr messages
        # (such as "task does not exist", so we look for the 'Traceback'
        # string.  This only works for python, so we'll need to revisit
        # this in the future when we support subcommands written in other
        # languages.
        if report and 'Traceback' in err:
            _track_err(pool, exit_code, err, conf)

    return exit_code


def wait_and_capture(subproc):
    """
    Run a subprocess and capture its stderr.

    :param subproc: Subprocess to capture
    :type subproc: Popen
    :returns: exit code of subproc
    :rtype: int
    """

    err = ''
    while subproc.poll() is None:
        line = subproc.stderr.readline().decode('utf-8')
        err += line
        sys.stderr.write(line)
        sys.stderr.flush()

    exit_code = subproc.poll()

    return exit_code, err


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
            'properties': properties}

    if 'core.email' in conf:
        data['userId'] = conf['core.email']
    else:
        data['anonymousId'] = session_id

    _segment_request('track', data)


def segment_identify(conf):
    """
    Send a segment.io 'identify' event

    :param conf: dcos config file
    :type conf: Toml
    :rtype: None
    """

    if 'core.email' in conf:
        data = {'userId': conf.get('core.email')}
        _segment_request('identify', data)


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


def _track_err(pool, exit_code, err, conf):
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
    :rtype: None
    """

    # Segment.io calls are async, but rollbar is not, so for
    # parallelism, we must call segment first.
    _segment_track_err(pool, conf, err, exit_code)
    _rollbar_track_err(conf, err, exit_code)


def _segment_track_cli(pool, conf):
    """
    Send segment.io cli event.

    :param pool: thread pool
    :type pool: ThreadPoolExecutor
    :param conf: dcos config file
    :type conf: Toml
    :rtype: None
    """

    props = _base_properties(conf)
    pool.submit(_segment_track, SEGMENT_IO_CLI_EVENT, conf, props)


def _segment_track_err(pool, conf, err, exit_code):
    """
    Send segment.io error event.

    :param pool: thread pool
    :type segment: ThreadPoolExecutor
    :param conf: dcos config file
    :type conf: Toml
    :param err: stderr of tracked process
    :type err: str
    :param exit_code: exit code of tracked process
    :type exit_code: int
    :rtype: None
    """

    props = _base_properties(conf)
    props['err'] = err
    props['exit_code'] = exit_code
    pool.submit(_segment_track, SEGMENT_IO_CLI_ERROR_EVENT, conf, props)


def _rollbar_track_err(conf, err, exit_code):
    """
    Report to rollbar.  Synchronous.

    :param exit_code: exit code of tracked process
    :type exit_code: int
    :param err: stderr of tracked process
    :type err: str
    :param conf: dcos config file
    :type conf: Toml
    :rtype: None
    """

    props = _base_properties(conf)
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

    # avoid circular import
    import dcoscli.main

    args = docopt.docopt(dcoscli.main.__doc__,
                         help=False,
                         options_first=True)
    return args['<command>']


def _base_properties(conf=None):
    """
    These properties are sent with every analytics event.

    :param conf: dcos config file
    :type conf: Toml
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

    return {
        'cmd': cmd,
        'full_cmd': full_cmd,
        'dcoscli.version': dcoscli.version,
        'python_version': str(sys.version_info),
        'config': json.dumps(list(conf.property_items())),
        'DCOS_HOSTNAME': dcos_hostname,
    }
