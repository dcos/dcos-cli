
from __future__ import absolute_import, print_function

import json
import requests
import urlparse

def start_tasks(base_url, cfg, t="long"):
    return requests.post(urlparse.urljoin(base_url, t), data=json.dumps(cfg)).text

def stop_tasks(base_url, cnt):
    return requests.get(
        urlparse.urljoin(base_url, "stop?num={0}".format(cnt))).text
