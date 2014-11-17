
import itertools

from .scheduler import CURRENT as MARATHON

def app(prefix, parsed_args, **kwargs):
    return [x.id for x in MARATHON.apps(prefix)]
