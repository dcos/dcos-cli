import fnmatch
import itertools

from dcos import http, util
from dcos.errors import DCOSException

from six.moves import urllib

logger = util.get_logger(__name__)


def get_master(config=None):
    """Create a Master object using the URLs stored in the user's
    configuration.

    :param config: config
    :type config: Toml
    :returns: master state object
    :rtype: Master
    """

    return Master(get_master_client(config).get_state())


def get_master_client(config=None):
    """Create a Mesos master client using the URLs stored in the user's
    configuration.

    :param config: config
    :type config: Toml
    :returns: mesos master client
    :rtype: MasterClient
    """

    if config is None:
        config = util.get_config()

    mesos_url = _get_mesos_url(config)
    return MasterClient(mesos_url)


def _get_mesos_url(config):
    """
    :param config: configuration
    :type config: Toml
    :returns: url for the Mesos master
    :rtype: str
    """

    mesos_master_url = config.get('core.mesos_master_url')
    if mesos_master_url is None:
        dcos_url = util.get_config_vals(config, ['core.dcos_url'])[0]
        return urllib.parse.urljoin(dcos_url, 'mesos/')
    else:
        return mesos_master_url


class MasterClient:
    """Client for communicating with the Mesos master

    :param url: URL for the Mesos master
    :type url: str
    """

    def __init__(self, url):
        self._base_url = url

    def _create_url(self, path):
        """Creates the url from the provided path.

        :param path: url path
        :type path: str
        :returns: constructed url
        :rtype: str
        """

        return urllib.parse.urljoin(self._base_url, path)

    def get_state(self):
        """Get the Mesos master state json object

        :returns: Mesos' master state json object
        :rtype: dict
        """

        return http.get(self._create_url('master/state.json')).json()

    def shutdown_framework(self, framework_id):
        """Shuts down a Mesos framework

        :returns: None
        """

        logger.info('Shutting down framework {}'.format(framework_id))

        data = 'frameworkId={}'.format(framework_id)
        http.post(self._create_url('master/shutdown'), data=data)


class Master(object):
    """Mesos Master Model

    :param state: Mesos master state json
    :type state: dict
    """

    def __init__(self, state):
        self._state = state

    def state(self):
        """Returns master's master/state.json.

        :returns: state.json
        :rtype: dict
        """

        return self._state

    def slave(self, fltr):

        """Returns the slave that has `fltr` in its id.  Raises a
        DCOSException if there is not exactly one such slave.

        :param fltr: filter string
        :type fltr: str
        :returns: the slave that has `fltr` in its id
        :rtype: Slave
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
        :rtype: [Slave]
        """

        return [Slave(slave)
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
    def tasks(self, fltr="", completed=False):
        """Returns tasks running under the master

        :param fltr: May be a substring or unix glob pattern.  Only
                     return tasks whose 'id' matches `fltr`.
        :type fltr: str
        :param completed: also include completed tasks
        :type completed: bool
        :returns: a list of tasks
        :rtype: [Task]

        """

        keys = ['tasks']
        if completed:
            keys = ['completed_tasks']

        tasks = []
        for framework in self._framework_dicts(completed, completed):
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

        for f in self._framework_dicts(inactive=True):
            if f['id'] == framework_id:
                return Framework(f)
        raise DCOSException('No Framework with id [{}]'.format(framework_id))

    def frameworks(self, inactive=False, completed=False):
        """Returns a list of all frameworks

        :param inactive: also include inactive frameworks
        :type inactive: bool
        :param completed: also include completed frameworks
        :type completed: bool
        :returns: a list of frameworks
        :rtype: [Framework]
        """

        return [Framework(f)
                for f in self._framework_dicts(inactive, completed)]

    def _framework_dicts(self, inactive=False, completed=False):
        """Returns a list of all frameworks as their raw dictionaries

        :param inactive: also include inactive frameworks
        :type inactive: bool
        :param completed: also include completed frameworks
        :type completed: bool
        :returns: a list of frameworks
        :rtype: [dict]
        """

        keys = ['frameworks']
        if completed:
            keys.append('completed_frameworks')
        for framework in _merge(self.state(), *keys):
            if inactive or framework['active']:
                yield framework


class Slave(object):
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

    def dict(self):
        return self._framework

    def __getitem__(self, name):
        return self._framework[name]


class Task(object):
    """Mesos Task Model.  Created from the Task objects sent in master's
    state.json, which is in turn created from mesos' Task protobuf
    object.

    :param task: task properties
    :type task: dict
    :param master: mesos master
    :type master: Master
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
