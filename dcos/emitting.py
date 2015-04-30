from __future__ import print_function

import abc
import collections
import json
import os
import pydoc
import re
import sys

import pager
import pygments
import six
from dcos import constants, errors, util
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
    :type event: str, dict, list, or dcos.errors.Error
    """

    pager_command = os.environ.get(constants.DCOS_PAGER_COMMAND_ENV)

    if event is None:
        # Do nothing
        pass

    elif isinstance(event, six.string_types):
        _page(event, pager_command)

    elif isinstance(event, errors.Error):
        print(event.error(), file=sys.stderr)

    elif (isinstance(event, collections.Mapping) or
          isinstance(event, collections.Sequence) or isinstance(event, bool) or
          isinstance(event, six.integer_types) or isinstance(event, float)):
        # These are all valid JSON types let's treat them different
        processed_json = _process_json(event, pager_command)
        _page(processed_json, pager_command)

    else:
        logger.debug('Printing unknown type: %s, %r.', type(event), event)
        _page(event, pager_command)


def _process_json(event, pager_command):
    """Conditionally highlights the supplied JSON value.

    :param event: event to emit to stdout
    :type event: str, dict, list, or dcos.errors.Error
    :returns: String representation of the supplied JSON value,
              possibly syntax-highlighted.
    :rtype: str
    """

    json_output = json.dumps(event, sort_keys=True, indent=2)

    # Strip trailing whitespace
    json_output = re.sub(r'\s+$', '', json_output, 0, re.M)

    force_colors = False  # TODO(CD): Introduce a --colors flag

    if not sys.stdout.isatty():
        if force_colors:
            return _highlight_json(json_output)
        else:
            return json_output

    supports_colors = not util.is_windows_platform()

    pager_is_set = pager_command is not None

    should_highlight = force_colors or supports_colors and not pager_is_set

    if should_highlight:
        json_output = _highlight_json(json_output)

    return json_output


def _page(output, pager_command=None):
    """Conditionally pipes the supplied output through a pager.

    :param output:
    :type output: object
    :param pager_command:
    :type pager_command: str
    """

    output = str(output)

    if pager_command is None:
        pager_command = 'less -R'

    if not sys.stdout.isatty() or util.is_windows_platform():
        print(output)
        return

    num_lines = output.count('\n')
    exceeds_tty_height = pager.getheight() - 1 < num_lines

    if exceeds_tty_height:
        pydoc.pipepager(output, cmd=pager_command)
    else:
        print(output)


def _highlight_json(json_value):
    """
    :param json_value: JSON value to syntax-highlight
    :type json_value: dict, list, number, string, boolean, or None
    :returns: A string representation of the supplied JSON value,
              highlighted for a terminal that supports ANSI colors.
    :rtype: str
    """

    return pygments.highlight(
        json_value, JsonLexer(), Terminal256Formatter()).strip()


DEFAULT_HANDLER = print_handler
"""The default handler for an emitter: :py:func:`print_handler`."""
