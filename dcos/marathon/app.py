
import copy
import itertools
import json

import mesos.cli.util

from .. import log
from . import task
from . import util

class Application(util.ServerRequest):

    def __init__(self, items):
        self.__items = items

    def __getitem__(self, name):
        return self.__items[name]

    @property
    def _base_url(self):
        return "/v2/apps/{0}".format(self.id)

    @property
    def config(self):
        return self._version(self.version)

    @mesos.cli.util.CachedProperty(ttl=30)
    def state(self):
        return self._req("get")["app"]

    @mesos.cli.util.CachedProperty(ttl=30)
    def tasks(self):
        return [task.Task(x) for x in self._req("get", "tasks")["tasks"]]

    @mesos.cli.util.memoize
    def _version(self, i):
        return self._req("get", "versions/{0}".format(i))

    @mesos.cli.util.CachedProperty(ttl=30)
    def version_list(self):
        return self._req("get", "versions")["versions"]

    def versions(self, fltr=""):
        return itertools.ifilter(lambda x: fltr in x["version"],
            itertools.imap(lambda x: self._version(x), self.version_list))

    @property
    def started(self):
        return self.state["instances"] > 0

    @property
    def status(self):
        if len(filter(lambda x: x.healthy is False, self.tasks)) > 0:
            return "degraded"
        elif self.started:
            return "up"
        else:
            return "down"

    # ----- Commands

    def start(self):
        if self.started:
            log.fatal("{0} has already been started".format(self.id))

        for v in self.version_list[-2::-1]:
            i = self._version(v)["instances"]
            if i == 0:
                continue

            return self._req("put", data=json.dumps({ "instances": i }))

        log.fatal("app has never been started, try setting a number of " \
            "instances to run")

    def stop(self):
        if not self.started:
            log.fatal("{0} has already been stopped".format(self.id))

        return self.restart(True)

    def destroy(self):
        return self._req("delete")

    def restart(self, scale=False):
        return self._req("delete", "tasks?scale={0}".format(json.dumps(scale)))

    def update(self, cfg):
        return self._req("put", data=cfg)
