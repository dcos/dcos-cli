import functools
import sys
import time

import six

from dcos import emitting, util
from dcos.errors import DCOSException

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
