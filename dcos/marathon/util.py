
import os
import requests
import urlparse

from .. import log
from .. import data
from .cfg import CURRENT as CONFIG

def get_data(name):
    return open(os.path.join(os.path.dirname(data.__file__), name), "rb").read()

class ServerRequest(object):

    _base_url = "/v2/apps/"
    _headers = { "content-type": "application/json" }

    def _req(self, method, url=None, **kwargs):
        if not "headers" in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(self._headers)

        u = [ self._base_url ]
        if url:
            u += [ url ]
        try:
            return getattr(requests, method)(urlparse.urljoin(
                CONFIG.url, "/".join(u)), **kwargs).json()
        except ValueError:
            return None
        except requests.exceptions.ConnectionError:
            log.fatal(MISSING_SERVER.format(CONFIG.host))
