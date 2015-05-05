import json
import os
import sys
import uuid

import dcoscli
import requests
import rollbar
from concurrent.futures import ThreadPoolExecutor
from dcos import util
from dcoscli.constants import (ROLLBAR_SERVER_POST_KEY,
                               SEGMENT_IO_CLI_ERROR_EVENT,
                               SEGMENT_IO_CLI_EVENT, SEGMENT_IO_WRITE_KEY_DEV,
                               SEGMENT_IO_WRITE_KEY_PROD, SEGMENT_URL)
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

    rollbar.init(ROLLBAR_SERVER_POST_KEY,
                 'prod' if _is_prod() else 'dev')

    conf = util.get_config()
    report = conf.get('core.reporting', True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        if report:
            _segment_track_cli(pool, conf)

        exit_code, err = _wait_and_capture(subproc)

        # We only want to catch exceptions, not other stderr messages
        # (such as "task does not exist", so we look for the 'Traceback'
        # string.  This only works for python, so we'll need to revisit
        # this in the future when we support subcommands written in other
        # languages.
        if report and 'Traceback' in err:
            _track_err(pool, exit_code, err, conf)

    return exit_code


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
    else:
        data = {'anonymousId': session_id}

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

    key = SEGMENT_IO_WRITE_KEY_PROD if _is_prod() else \
        SEGMENT_IO_WRITE_KEY_DEV

    try:
        requests.post('{}/{}'.format(SEGMENT_URL, path),
                      json=data,
                      auth=HTTPBasicAuth(key, ''),
                      timeout=1)
    except Exception as e:
        logger.exception(e)


def _is_prod():
    """ True if this process is in production. """
    return os.environ.get('DCOS_PRODUCTION', 'true') != 'false'


def _wait_and_capture(subproc):
    """
    Run a subprocess and capture its stderr.

    :param subproc: Subprocess to capture
    :type subproc: Popen
    :returns: exit code of subproc
    :rtype: int
    """

    err = ''
    while subproc.poll() is None:
        err_buff = subproc.stderr.read().decode('utf-8')
        sys.stderr.write(err_buff)
        err += err_buff

    exit_code = subproc.poll()

    return exit_code, err


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

    try:
        rollbar.report_message(err, 'error', extra_data=props)
    except Exception as e:
        logger.exception(e)


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
        cmd = 'dcos ' + sys.argv[1]
        full_cmd = 'dcos ' + ' '.join(sys.argv[1:])
    else:
        cmd = 'dcos'
        full_cmd = 'dcos'

    return {
        'cmd': cmd,
        'full_cmd': full_cmd,
        'dcoscli.version': dcoscli.version,
        'python_version': str(sys.version_info),
        'config': json.dumps(list(conf.property_items()))
    }
