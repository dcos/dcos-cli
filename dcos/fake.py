
from __future__ import absolute_import, print_function

import json
import requests
import urlparse

from mesos.cli.master import CURRENT as MASTER

def start_tasks(base_url, cfg):
    if not isinstance(cfg, str):
        cfg = json.dumps(cfg)
    return requests.post(urlparse.urljoin(base_url, "start"),
        data=cfg).text

def stop_tasks(base_url, cnt):
    return requests.get(
        urlparse.urljoin(base_url, "stop?num={0}".format(cnt))).text

def list_tasks(name):
    tasks = [t for t in MASTER.tasks(active_only=True, fltr=name)
        if t["id"].index(name) == 0]

    print("Number of nodes: {0}".format(len(tasks)))
    print("Hostnames:")
    for t in tasks:
        print("\t{0}".format(t.slave["hostname"]))
