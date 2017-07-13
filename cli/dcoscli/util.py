import sys

from functools import wraps

import docopt

from dcos import emitting

emitter = emitting.FlatEmitter()


def decorate_docopt_usage(func):
    """Handle DocoptExit exception

    :param func: function
    :type func: function
    :return: wrapped function
    :rtype: function
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except docopt.DocoptExit as e:
            emitter.publish("Command not recognized\n")
            emitter.publish(e)
            return 1
        return result
    return wrapper


def confirm(prompt, yes):
    """
    :param prompt: message to display to the terminal
    :type prompt: str
    :param yes: whether to assume that the user responded with yes
    :type yes: bool
    :returns: True if the user responded with yes; False otherwise
    :rtype: bool
    """

    if yes:
        return True
    else:
        count = 0
        while count < 3:
            sys.stdout.write('{} [yes/no] '.format(prompt))
            sys.stdout.flush()
            response = _read_response().lower()
            if response == 'yes' or response == 'y':
                return True
            elif response == 'no' or response == 'n':
                return False
            else:
                msg = "'{}' is not a valid response.".format(response)
                emitter.publish(msg)
                count += 1
        return False


def confirm_text(prompt, confirmation_text):
    """
    :param prompt: message to display to the terminal
    :type prompt: str
    :param expected_text: The text to compare user input to.
    :type expected_text: str
    :returns: True if the user replies with the expected text; False otherwise
    :rtype: bool
    """

    count = 0
    while count < 3:
        sys.stdout.write('{}: '.format(prompt))
        sys.stdout.flush()
        response = _read_response()
        if response == confirmation_text:
            return True
        else:
            msg = "Expected '{}'. You supplied '{}'.".format(
                confirmation_text,
                response
            )
            emitter.publish(msg)
            count += 1
    return False


def _read_response():
    """
    :returns: The content of STDIN
    :rtype: str
    """
    return sys.stdin.readline().strip()
