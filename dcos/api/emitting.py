from __future__ import print_function

import abc
import collections
import json
import sys

import pygments
from dcos.api import errors, util
from pygments.formatters import Terminal256Formatter
from pygments.lexers import JsonLexer

try:
    basestring = basestring
except NameError:
    # We are in python3 define basestring as str
    basestring = str

logger = util.get_logger(__name__)


class Emitter(object):
    """Abstract class for emitting events."""

    @abc.abstractmethod
    def publish(self, event):
        """Publishes an event.

        :param event: event to publish
        :type event: any
        """

        raise NotImplementedError


class FlatEmitter(Emitter):
    """Simple emitter that sends all publish events to the provided handler.
    If no handler is provider then use :py:const:`DEFAULT_HANDLER`.

    :param handler: event handler to call when publish is called
    :type handler: func(event) where event is defined in
                   :py:func:`FlatEmitter.publish`
    """

    def __init__(self, handler=None):
        if handler is None:
            self._handler = DEFAULT_HANDLER
        else:
            self._handler = handler

    def publish(self, event):
        """Publishes an event.

        :param event: event to publish
        :type event: any
        """

        self._handler(event)


def print_handler(event):
    """Default handler for printing event to stdout.

    :param event: event to emit to stdout
    :type event: str, dict or dcos.api.errors.Error
    """

    if event is None:
        # Do nothing
        pass

    elif isinstance(event, basestring):
        print(event)

    elif isinstance(event, collections.Mapping) or isinstance(event, list):
        json_output = json.dumps(event, sort_keys=True, indent=2)

        supports_colors = sys.platform != 'win32'  # Note: Not tested on Win32

        if sys.stdout.isatty() and supports_colors:
            json_output = pygments.highlight(
                json_output, JsonLexer(), Terminal256Formatter()).strip()

        print(json_output)

    elif isinstance(event, errors.Error):
        print(event.error(), file=sys.stderr)

    else:
        logger.error(
            'Unable to print event. Type not supported: %s, %r.',
            type(event),
            event)


DEFAULT_HANDLER = print_handler
"""The default handler for an emitter: :py:func:`print_handler`."""
