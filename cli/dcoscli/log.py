import contextlib
import datetime
import functools
import json
import sys
import time

import six
from six.moves import urllib

from dcos import config, emitting, http, packagemanager, sse, util
from dcos.cosmos import get_cosmos_url
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException,
                         DCOSException,
                         DCOSHTTPException,
                         DefaultError)

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def _no_file_exception():
    return DCOSException('No files exist. Exiting.')


def log_files(mesos_files, follow, lines):
    """Print the contents of the given `mesos_files`.  Behaves like unix
    tail.

    :param mesos_files: file objects to print
    :type mesos_files: [MesosFile]
    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :rtype: None
    """

    fn = functools.partial(_read_last_lines, lines)
    curr_header, mesos_files = _stream_files(None, fn, mesos_files)
    if not mesos_files:
        raise _no_file_exception()

    while follow:
        # This flush is needed only for testing, since stdout is fully
        # buffered (as opposed to line-buffered) when redirected to a
        # pipe.  So if we don't flush, our --follow tests, which use a
        # pipe, never see the data
        sys.stdout.flush()

        curr_header, mesos_files = _stream_files(curr_header,
                                                 _read_rest,
                                                 mesos_files)
        if not mesos_files:
            raise _no_file_exception()
        time.sleep(1)


def _stream_files(curr_header, fn, mesos_files):
    """Apply `fn` in parallel to each file in `mesos_files`.  `fn` must
    return a list of strings, and these strings are then printed
    serially as separate lines.

    `curr_header` is the most recently printed header.  It's used to
    group lines.  Each line has an associated header (e.g. a string
    representation of the MesosFile it was read from), and we only
    print the header before printing a line with a different header
    than the previous line.  This effectively groups lines together
    when the have the same header.

    :param curr_header: Most recently printed header
    :type curr_header: str
    :param fn: function that reads a sequence of lines from a MesosFile
    :type fn: MesosFile -> [str]
    :param mesos_files: files to read
    :type mesos_files: [MesosFile]
    :returns: Returns the most recently printed header, and a list of
        files that are still reachable.  Once we detect a file is
        unreachable, we stop trying to read from it.
    :rtype: (str, [MesosFile])
    """

    reachable_files = list(mesos_files)

    # TODO switch to map
    for job, mesos_file in util.stream(fn, mesos_files):
        try:
            lines = job.result()
        except DCOSException as e:
            # The read function might throw an exception if read.json
            # is unavailable, or if the file doesn't exist in the
            # sandbox.  In any case, we silently remove the file and
            # continue.
            logger.exception("Error reading file: {}".format(e))

            reachable_files.remove(mesos_file)
            continue

        if lines:
            curr_header = _output(curr_header,
                                  len(reachable_files) > 1,
                                  six.text_type(mesos_file),
                                  lines)

    return curr_header, reachable_files


def _output(curr_header, output_header, header, lines):
    """Prints a sequence of lines.  If `header` is different than
    `curr_header`, first print the header.

    :param curr_header: most recently printed header
    :type curr_header: str
    :param output_header: whether or not to output the header
    :type output_header: bool
    :param header: header for `lines`
    :type header: str
    :param lines: lines to print
    :type lines: [str]
    :returns: `header`
    :rtype: str
    """

    if lines:
        if output_header and header != curr_header:
            emitter.publish('===> {} <==='.format(header))
        if lines == ['']:
            emitter.publish(DefaultError('No logs for this task'))
        for line in lines:
            emitter.publish(line)
    return header


# A liberal estimate of a line size.  Used to estimate how much data
# we need to fetch from a file when we want to read N lines.
LINE_SIZE = 200


def _read_last_lines(num_lines, mesos_file):
    """Returns the last `num_lines` of a file, or less if the file is
    smaller.  Seeks to EOF.

    :param num_lines: number of lines to read
    :type num_lines: int
    :param mesos_file: file to read
    :type mesos_file: MesosFile
    :returns: lines read
    :rtype: [str]
    """

    file_size = mesos_file.size()

    # estimate how much data we need to fetch to read `num_lines`.
    fetch_size = LINE_SIZE * num_lines

    end = file_size
    start = max(end - fetch_size, 0)
    data = ''
    while True:
        # fetch data
        mesos_file.seek(start)
        data = mesos_file.read(end - start) + data

        # break if we have enough lines
        data_tmp = _strip_trailing_newline(data)
        lines = data_tmp.split('\n')
        if len(lines) > num_lines:
            ret = lines[-num_lines:]
            break
        elif start == 0:
            ret = lines
            break

        # otherwise shift our read window and repeat
        end = start
        start = max(end - fetch_size, 0)

    mesos_file.seek(file_size)
    return ret


def _read_rest(mesos_file):
    """ Reads the rest of the file, and returns the lines.

    :param mesos_file: file to read
    :type mesos_file: MesosFile
    :returns: lines read
    :rtype: [str]
    """
    data = mesos_file.read()
    if data == '':
        return []
    else:
        data_tmp = _strip_trailing_newline(data)
        return data_tmp.split('\n')


def _strip_trailing_newline(s):
    """Returns a modified version of the string with the last character
    truncated if it's a newline.

    :param s: string to trim
    :type s: str
    :returns: modified string
    :rtype: str
    """

    if s == "":
        return s
    else:
        return s[:-1] if s[-1] == '\n' else s


def has_journald_capability():
    """ functions checks LOGGING capability.

    :return: does cosmos have LOGGING capability.
    :rtype: bool
    """
    return packagemanager.PackageManager(
        get_cosmos_url()).has_capability('LOGGING')


def has_log_v2_capability():
    """ function checks the cosmos capability LOGGING_V2
        to know if `dcos-log` suppports v2 on the cluster.

        :return: cosmos has LOGGING_V2 capability.
        :rtype: bool
    """

    return packagemanager.PackageManager(
        get_cosmos_url()).has_capability('LOGGING_V2')


def dcos_log_enabled(version=1):
    """ functions checks the cosmos capability LOGGING
        to know if `dcos-log` is enabled on the cluster.

    :return: if journald logging enabled base on strategy.
    :rtype: bool
    """

    # https://github.com/dcos/dcos/blob/master/gen/calc.py#L151
    if version == 1:
        return logging_strategy() == 'journald'
    elif version == 2:
        return has_log_v2_capability()
    raise DCOSException(
        "invalid dcos-log version {}. Must be 1 or 2".format(version))


def logging_strategy():
    """ function returns logging strategy

    :return: logging strategy.
    :rtype: str
    """
    # default strategy is sandbox logging.
    strategy = 'logrotate'

    if not has_journald_capability():
        return strategy

    base_url = config.get_config_val("core.dcos_url")
    url = urllib.parse.urljoin(base_url, '/dcos-metadata/ui-config.json')

    if not base_url:
        raise config.missing_config_exception(['core.dcos_url'])

    try:
        response = http.get(url).json()
    except (DCOSAuthenticationException, DCOSAuthorizationException):
        raise
    except DCOSException:
        emitter.publish('Unable to determine logging mechanism for '
                        'your cluster. Defaulting to files API.')
        return strategy

    try:
        strategy = response['uiConfiguration']['plugins']['mesos']['logging-strategy']  # noqa: ignore=F403,E501
    except Exception:
        pass

    return strategy


def follow_logs(url):
    """ Function will use dcos.sse.get to subscribe to server sent events
        and follow the real time logs. The log entry has the following format:
        `date _HOSTNAME SYSLOG_IDENTIFIER[_PID]: MESSAGE`, where
        _HOSTNAME, SYSLOG_IDENTIFIER and _PID are optional fields.
        MESSAGE is also optional, however we should skip the entire log entry
        if MESSAGE is not found.

    :param url: `dcos-log` streaming endpoint
    :type url: str
    """
    for entry in sse.get(url):
        # the sse library does not handle sse comments properly
        # making entry.data empty. As a workaround we can check if `entry.data`
        # is not empty.
        if not entry.data:
            continue

        try:
            entry_json = json.loads(entry.data)
        except ValueError:
            # if the SSE message is not a json, emit the raw data.
            emitter.publish(entry.data)
            continue

        if 'fields' not in entry_json:
            raise DCOSException(
                'Missing `fields` in log entry: {}'.format(entry))

        # `MESSAGE` is optional field. Skip the log entry if it's missing.
        if 'MESSAGE' not in entry_json['fields']:
            continue

        line = ''
        if 'realtime_timestamp' in entry_json:
            # entry.RealtimeTimestamp returns a unix time in microseconds
            # https://www.freedesktop.org/software/systemd/man/sd_journal_get_realtime_usec.html
            timestamp = int(entry_json['realtime_timestamp'] / 1000000)
            line = '{}: '.format(
                datetime.datetime.fromtimestamp(timestamp).strftime(
                    '%Y-%m-%d %H:%m:%S'))

        line += entry_json['fields']['MESSAGE']
        emitter.publish(line)


def is_success(code):
    """ Returns the expected response codes for HTTP GET requests
    :param code: HTTP response codes
    :type code: int
    """
    if (200 <= code < 300) or code in [404, 500]:
        return True
    return False


def print_logs_range(url):
    """ Make a get request to `dcos-log` range endpoint.
        the function will print out logs to stdout and exit.

    :param url: `dcos-log` endpoint
    :type url: str
    """
    with contextlib.closing(http.get(url, is_success=is_success,
                                     headers={'Accept': 'text/plain'})) as r:

        if r.status_code == 500:
            raise DCOSException(
                '{} Error message: {}'.format(DCOSHTTPException(r), r.text))
        if r.status_code == 404:
            raise DCOSException('No files exist. Exiting.')
        if r.status_code == 204:
            raise DCOSException('No logs found')

        if r.status_code != 200:
            raise DCOSException(
                'Error getting logs. Url: {};'
                'response code: {}'.format(url, r.status_code))

        for line in r.iter_lines():
            emitter.publish(line.decode('utf-8', 'ignore'))
