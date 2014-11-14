
from __future__ import absolute_import, print_function

import argparse
import functools
import logging
import os

import dcos

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
