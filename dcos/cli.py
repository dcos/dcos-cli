
from __future__ import absolute_import, print_function

import argparse
import functools
import json
import logging
import os
import select

import blessings
import dcos
import pygments.lexers
import pygments.formatters

from . import log
from .cfg import CURRENT as CFG
from .parser import ArgumentParser


def init(parser=None):

    def decorator(fn):
        @handle_signals
        @log.duration
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            cmd_args = parser.parse_args() if parser else None

            log_level = getattr(logging, CFG["log_level"].upper())
            logging.basicConfig(
                level=log_level,
                filename=CFG["log_file"]
            )

            if CFG["debug"] == "true":
                debug_requests()

            return fn(cmd_args, *args, **kwargs)
        return wrapper
    return decorator


def parser(**kwargs):
    parser_inst = ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        **kwargs
    )

    parser_inst.add_argument(
        "-v", "--version",
        action="version", version="%(prog)s {0}".format(dcos.__version__)
    )
    return parser_inst


def handle_signals(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KeyboardInterrupt:
            if CFG["debug"] == "true":
                raise
    return wrapper


def cmds(short=False):
    def fltr(cmd):
        if not cmd.startswith("dcos-"):
            return False
        return True

    cmds = set([])
    for path in os.environ.get("PATH").split(os.pathsep):
        try:
            cmds = cmds.union(filter(fltr, os.listdir(path)))
        except OSError:
            pass

    if short:
        cmds = [x.split("-", 1)[-1] for x in cmds]

    return sorted(cmds)


def debug_requests():
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1


def has_data(fd):
    r, w, e = select.select([ fd ], [], [], 0)
    return fd in r


def edit_txt(content):
    with tempfile.NamedTemporaryFile() as fobj:
        fobj.write(content)
        fobj.flush()

        subprocess.call(shlex.split(os.environ.get("EDITOR")) + [fobj.name])

        return re.sub("//.*$", "", open(fobj.name, "rb").read(), flags=re.M)

json_lexer = pygments.lexers.get_lexer_by_name("json")
console_formatter = pygments.formatters.Terminal256Formatter()


def json_fmt(obj):
    out = json.dumps(obj, indent=4)
    if blessings.Terminal().is_a_tty:
        return pygments.highlight(out, json_lexer, console_formatter)
    else:
        return out


def json_out(obj):
    print(json_fmt(obj))
