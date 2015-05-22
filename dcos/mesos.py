import fnmatch
import itertools

import dcos.http
from dcos import util
from dcos.errors import DCOSException

from six.moves import urllib

logger = util.get_logger(__name__)


def get_master(config=None):
    """Create a MesosMaster object using the url stored in the
    'core.master' property of the user's config.

    :param config: config
    :type config: Toml
    :returns: MesosMaster object
    :rtype: MesosMaster

    """
    if config is None:
        config = util.get_config()

    mesos_url = get_mesos_url(config)
    return MesosMaster(mesos_url)


def get_mesos_url(config):
    mesos_master_url = config.get('core.mesos_master_url')
    if mesos_master_url is None:
        dcos_url = util.get_config_vals(config, ['core.dcos_url'])[0]
        return urllib.parse.urljoin(dcos_url, 'mesos/')
    else:
        return mesos_master_url


MESOS_TIMEOUT = 3


class MesosMaster(object):
    """Mesos Master Model

    :param url: master url (e.g. "http://localhost:5050")
    :type url: str
    """

    def __init__(self, url):
        self._url = url
        self._state = None

    def state(self):
        """Returns master's /master/state.json.  Fetches and saves it if we
        haven't already.

        :returns: state.json
        :rtype: dict
        """

        if not self._state:
            self._state = self.fetch('master/state.json').json()
        return self._state

    def slave(self, fltr):

        """Returns the slave that has `fltr` in its id.  Raises a
        DCOSException if there is not exactly one such slave.

        :param fltr: filter string
        :type fltr: str
        :returns: the slave that has `fltr` in its id
        :rtype: MesosSlave
        """

        slaves = self.slaves(fltr)

        if len(slaves) == 0:
            raise DCOSException('Slave {} no longer exists'.format(fltr))

        elif len(slaves) > 1:
            matches = ['\t{0}'.format(slave.id) for slave in slaves]
            raise DCOSException(
                "There are multiple slaves with that id. " +
                "Please choose one: {}".format('\n'.join(matches)))

        else:
            return slaves[0]

    def slaves(self, fltr=""):
        """Returns those slaves that have `fltr` in their 'id'

        :param fltr: filter string
        :type fltr: str
        :returns: Those slaves that have `fltr` in their 'id'
        :rtype: [MesosSlave]
        """

        return [MesosSlave(slave)
                for slave in self.state()['slaves']
                if fltr in slave['id']]

    def task(self, fltr):
        """Returns the task with `fltr` in its id.  Raises an exception if
        there is not exactly one such task.

        :param fltr: filter string
        :type fltr: str
        :returns: the task that has `fltr` in its id
        :rtype: Task
        """

        tasks = self.tasks(fltr)

        if len(tasks) == 0:
            raise DCOSException(
                'Cannot find a task containing "{}"'.format(fltr))

        elif len(tasks) > 1:
            msg = ["There are multiple tasks with that id. Please choose one:"]
            msg += ["\t{0}".format(t["id"]) for t in tasks]
            raise DCOSException('\n'.join(msg))

        else:
            return tasks[0]

    # TODO (thomas): need to filter on task state as well as id
    def tasks(self, fltr="", active_only=False):
        """Returns tasks running under the master

        :param fltr: May be a substring or unix glob pattern.  Only
                     return tasks whose 'id' matches `fltr`.
        :type fltr: str
        :param active_only: don't include completed tasks
        :type active_only: bool
        :returns: a list of tasks
        :rtype: [Task]

        """

        keys = ['tasks']
        if not active_only:
            keys = ['completed_tasks']

        tasks = []
        for framework in self._framework_dicts(active_only):
            tasks += \
                [Task(task, self)
                 for task in _merge(framework, *keys)
                 if fltr in task['id'] or
                 fnmatch.fnmatchcase(task['id'], fltr)]

        return tasks

    def framework(self, framework_id):
        """Returns a framework by id

        :param framework_id: the framework's id
        :type framework_id: int
        :returns: the framework
        :rtype: Framework
        """

        for f in self._framework_dicts(active_only=False):
            if f['id'] == framework_id:
                return Framework(f)
        raise DCOSException('No Framework with id [{}]'.format(framework_id))

    def frameworks(self, active_only=False):
        """Returns a list of all frameworks

        :param active_only: only include active frameworks
        :type active_only: bool
        :returns: a list of frameworks
        :rtype: [Framework]
        """

        return [Framework(f) for f in self._framework_dicts(active_only)]

    def _framework_dicts(self, active_only=False):
        """Returns a list of all frameworks as their raw dictionaries

        :param active_only: only include active frameworks
        :type active_only: bool
        :returns: a list of frameworks
        :rtype: [dict]
        """

        keys = ['frameworks']
        if not active_only:
            keys.append('completed_frameworks')
        return _merge(self.state(), *keys)

    @util.duration
    def fetch(self, path, **kwargs):
        """GET the resource located at `path`

        :param path: the URL path
        :type path: str
        :param **kwargs: requests.get kwargs
        :type **kwargs: dict
        :returns: the response object
        :rtype: Response
        """

        url = urllib.parse.urljoin(self._url, path)
        return dcos.http.get(url,
                             timeout=MESOS_TIMEOUT,
                             **kwargs)


class MesosSlave(object):
    """Mesos Slave Model

    :param slave: dictionary representing the slave.
                  retrieved from master/state.json
    :type slave: dict
    """

    def __init__(self, slave):
        self._slave = slave

    def __getitem__(self, name):
        return self._slave[name]


class Framework(object):
    """ Mesos Framework Model

    :param framework: framework properties
    :type framework: dict
    """

    def __init__(self, framework):
        self._framework = framework

    def __getitem__(self, name):
        return self._framework[name]


class Task(object):
    """Mesos Task Model.  Created from the Task objects sent in master's
    state.json, which is in turn created from mesos' Task protobuf
    object.

    :param task: task properties
    :type task: dict
    :param master: mesos master
    :type master: MesosMaster
    """

    def __init__(self, task, master):
        self._task = task
        self._master = master

    def dict(self):
        """
        :returns: dictionary representation of this Task
        :rtype: dict
        """
        return self._task

    def framework(self):
        """Returns the task's framework

        :returns" task's framework
        :rtype: Framework
        """

        return self._master.framework(self["framework_id"])

    def user(self):
        """Task owner

        :returns: task owner
        :rtype: str
        """

        return self.framework()['user']

    def __getitem__(self, name):
        return self._task[name]


def _merge(d, *keys):
    """ Merge multiple lists from a dictionary into one iterator.
        e.g. _merge({'a': [1, 2], 'b': [3]}, ['a', 'b']) ->
             iter(1, 2, 3)

    :param d: dictionary
    :type d: dict
    :param *keys: keys to merge
    :type *keys: [hashable]
    :returns: iterator
    :rtype: iter
    """

    return itertools.chain(*[d[k] for k in keys])
