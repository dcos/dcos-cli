
from __future__ import absolute_import, print_function

import os
import threading
from Queue import Queue
import uuid

from mesos.interface import Scheduler
from mesos.interface import mesos_pb2
from mesos.native import MesosSchedulerDriver as SchedulerDriver

TASKS = Queue()
CURRRENT = None

class FakeScheduler(Scheduler):

    _default_cmd = "while true; do sleep 100; done"

    def __init__(self, name, version, cmd=None):
        self.name = name
        self.version = version
        self.tasks_created = 0
        self.cmd = cmd or self._default_cmd
        self.tasks = Queue()
        self.set_driver()

    def __str__(self):
        return "{0}-{1}".format(self.name, self.version)

    def run(self):
        t = threading.Thread(target=self.driver.run)
        t.setDaemon(True)
        t.start()

    def set_driver(self):
        fwinfo = mesos_pb2.FrameworkInfo(user="", name=str(self))
        self.driver = SchedulerDriver(self, fwinfo, os.environ["MASTER"])

    def registered(self, driver, fwid, minfo):
        print("registered with framework ID [{0}]".format(fwid))

    def set_resource(self, a, x):
        a[x.name] = x.scalar.value
        return a

    def convert_offer(self, offer):
        return (offer, reduce(self.set_resource, offer.resources, {}))

    def resourceOffers(self, driver, offers):
        for offer, r in map(lambda x: self.convert_offer(x), offers):
            print("got resource offer [{0}]".format(offer.id.value))

            if TASKS.qsize() == 0:
                driver.declineOffer(offer.id)
                continue

            spec = TASKS.get()
            if len([v for k,v in r.iteritems() if spec.get(k, 0) > v]) > 0:
                TASKS.put(spec)
                driver.declineOffer(offer.id)
                continue

            task = self.make_task(spec, offer)
            print("Launching task on [{0}]".format(offer.hostname))
            driver.launchTasks(offer.id, [task])

    def make_task(self, spec, offer):
        task = mesos_pb2.TaskInfo(
            slave_id=offer.slave_id,
            command=self.make_cmd()
        )
        task.task_id.value = "{0}.{1}".format(self.name, uuid.uuid4())
        task.name = str(self)
        self.tasks.put(task.task_id)

        for k in [ "cpus", "mem" ]:
            r = task.resources.add()
            r.name = k
            r.type = mesos_pb2.Value.SCALAR
            r.scalar.value = spec[k]

        return task

    def make_cmd(self):
        cmd = mesos_pb2.CommandInfo()
        cmd.value = self._default_cmd
        return cmd

    def stop_task(self):
        if self.tasks.qsize() > 0:
            self.driver.killTask(self.tasks.get())
