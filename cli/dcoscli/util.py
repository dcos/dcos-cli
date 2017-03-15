from functools import wraps
import os
from shutil import copyfile
from tempfile import NamedTemporaryFile

import docopt

from dcos import emitting, subprocess

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


def edit_file(filename, validate=None):
    with NamedTemporaryFile() as temp_file_obj:
        copyfile(filename, temp_file_obj.name)

        editor = os.environ.get('EDITOR', 'vi')
        cmd = '%s %s' % (editor, temp_file_obj.name)
        emitter.publish('Executing: %s' % cmd)
        subprocess.Subproc().call(cmd, shell=True)

        if validate:
            if not validate(temp_file_obj):
                emitter.publish(
                    'File %s failed validation check. Not updating %s.'
                    % (temp_file_obj.name, filename))
                return False

        copyfile(temp_file_obj.name, filename)
        emitter.publish('Updated file: %s' % filename)
