
import itertools

import mesos.cli.util

from .. import log
from . import util
from . import app


class Scheduler(util.ServerRequest):

    @mesos.cli.util.memoize
    def app(self, _id):
        lst = list(self.apps(_id))

        if len(lst) == 0:
            log.fatal("Cannot find an app by that name.")
        elif len(lst) > 1:
            result = "There are multiple apps with that id. Please choose one: "
            for a in lst:
                result += "\n\t{0}".format(a.id)
            log.fatal(result)

        return lst[0]


    @mesos.cli.util.CachedProperty(ttl=30)
    def _apps(self):
        return [app.Application(x) for x in
            self._req("get").get("apps", [])]


    def apps(self, fltr=""):
        return itertools.ifilter(lambda x: fltr in x["id"], self._apps)


    def create(self, data):
        return self._req("post", data=data)


    @mesos.cli.util.memoize
    def task(self, _id):
        lst = list(self.tasks(_id))

        if len(lst) == 0:
            log.fatal("Cannot find a task by that name.")
        elif len(lst) > 1:
            result = "There are multiple tasks with that id. Please choose one: "
            for a in lst:
                result += "\n\t{0}".format(a.id)
            log.fatal(result)

        return lst[0]


    @mesos.cli.util.CachedProperty(ttl=30)
    def _tasks(self):
        return itertools.chain(*[a.tasks for a in self._apps])


    def tasks(self, fltr=""):
        return itertools.ifilter(lambda x: fltr in x.id, self._tasks)


CURRENT = Scheduler()
