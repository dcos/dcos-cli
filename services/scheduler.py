
from __future__ import absolute_import, print_function

import os

from mesos.interface import Scheduler
from mesos.interface import mesos_pb2
from mesos.native import MesosSchedulerDriver as SchedulerDriver

class FakeScheduler(Scheduler):

    def __init__(self, name, version):
        self.name = name
        self.version = version

    def get_driver(self):
        fwinfo = mesos_pb2.FrameworkInfo(
            user="",
            name="{0}-{1}".format(self.name, self.version))

        self.driver = SchedulerDriver(self, fwinfo, os.environ["MASTER"])
        return self.driver

    def registered(self, driver, fwid, minfo):
        print("registered with framework ID [{0}]".format(fwid))

    def resourceOffers(self, driver, offers):
        print("===============================")
        for offer in offers:
            print("got resource offer [{0}]".format(offer.id.value))
