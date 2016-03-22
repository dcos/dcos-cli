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
