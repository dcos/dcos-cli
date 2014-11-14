
from __future__ import absolute_import, print_function

import functools
import logging
import sys
import time

debug = logging.debug


def fatal(msg, code=1):
    sys.stdout.write(msg + "\n")
    logging.error(msg)
    sys.exit(code)


def fn(f, *args, **kwargs):
    logging.debug("{0}: {1} {2}".format(repr(f), args, kwargs))
    return f(*args, **kwargs)


def duration(fn):
    @functools.wraps(fn)
    def timer(*args, **kwargs):
        start = time.time()
        try:
            return fn(*args, **kwargs)
        finally:
            debug("duration: {0}.{1}: {2:2.2f}s".format(
                fn.__module__,
                fn.__name__,
                time.time() - start))

    return timer
