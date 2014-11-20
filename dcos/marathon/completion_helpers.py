
import itertools

from .. import log
from .scheduler import CURRENT as MARATHON

def app(prefix, parsed_args, **kwargs):
    return [x.id for x in MARATHON.apps(prefix)]

def service(prefix, parsed_args, **kwargs):
    return [x.id[4:] for x in MARATHON.apps("fwk-{0}".format(prefix))]
