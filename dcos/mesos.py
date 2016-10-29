import fnmatch
import itertools
import os
import pickle
import signal
import sys

# Generated protobuf code
import agent_pb2 as pba
import mesos_pb2 as pbm

from functools import partial

from google.protobuf.json_format import MessageToJson, Parse

from threading import Thread

from six.moves import urllib

from dcos import config, http, util
from dcos.errors import DCOSException, DCOSHTTPException

from queue import Queue

logger = util.get_logger(__name__)


def get_master(dcos_client=None):
    """Create a Master object using the url stored in the
    'core.mesos_master_url' property if it exists.  Otherwise, we use
    the `core.dcos_url` property

    :param dcos_client: DCOSClient
    :type dcos_client: DCOSClient | None
    :returns: master state object
    :rtype: Master
    """

    dcos_client = dcos_client or DCOSClient()
    return Master(dcos_client.get_master_state())


class DCOSClient(object):
    """Client for communicating with DC/OS"""

    def __init__(self):
        toml_config = config.get_config()

        self._dcos_url = config.get_config_val("core.dcos_url", toml_config)
        if self._dcos_url is None:
            raise config.missing_config_exception(['core.dcos_url'])
        self._mesos_master_url = config.get_config_val(
            'core.mesos_master_url', toml_config)

        self._timeout = config.get_config_val('core.timeout', toml_config)

    def get_dcos_url(self, path):
        """ Create a DC/OS URL

        :param path: the path suffix of the URL
        :type path: str
        :returns: DC/OS URL
        :rtype: str
        """

        return urllib.parse.urljoin(self._dcos_url, path)

    def master_url(self, path):
        """ Create a master URL

        :param path: the path suffix of the desired URL
        :type path: str
        :returns: URL that hits the master
        :rtype: str
        """

        base_url = (self._mesos_master_url or
                    urllib.parse.urljoin(self._dcos_url, 'mesos/'))
        return urllib.parse.urljoin(base_url, path)

    def slave_url(self, slave_id, private_url, path):
        """Create a slave URL

        :param slave_id: slave ID
        :type slave_id: str
        :param private_url: The slave's private URL derived from its
                            pid.  Used when we're accessing mesos
                            directly, rather than through DC/OS.
        :type private_url: str
        :param path: the path suffix of the desired URL
        :type path: str
        :returns: URL that hits the master
        :rtype: str

        """

        if self._mesos_master_url:
            return urllib.parse.urljoin(private_url, path)
        else:
            return urllib.parse.urljoin(self._dcos_url,
                                        'slave/{}/{}'.format(slave_id, path))

    def get_master_state(self):
        """Get the Mesos master state json object

        :returns: Mesos' master state json object
        :rtype: dict
        """

        url = self.master_url('master/state.json')
        return http.get(url, timeout=self._timeout).json()

    def get_slave_state(self, slave_id, private_url):
        """Get the Mesos slave state json object

        :param slave_id: slave ID
        :type slave_id: str
        :param private_url: The slave's private URL derived from its
                            pid.  Used when we're accessing mesos
                            directly, rather than through DC/OS.
        :type private_url: str
        :returns: Mesos' master state json object
        :rtype: dict

        """

        url = self.slave_url(slave_id, private_url, 'state.json')
        return http.get(url, timeout=self._timeout).json()

    def get_state_summary(self):
        """Get the Mesos master state summary json object

        :returns: Mesos' master state summary json object
        :rtype: dict
        """

        url = self.master_url('master/state-summary')
        return http.get(url, timeout=self._timeout).json()

    def slave_file_read(self, slave_id, private_url, path, offset, length):
        """See the master_file_read() docs

        :param slave_id: slave ID
        :type slave_id: str
        :param path: absolute path to read
        :type path: str
        :param private_url: The slave's private URL derived from its
                            pid.  Used when we're accessing mesos
                            directly, rather than through DC/OS.
        :type private_url: str
        :param offset: start byte location, or -1.  -1 means read no data, and
                       is used to fetch the size of the file in the response's
                       'offset' parameter.
        :type offset: int
        :param length: number of bytes to read, or -1.  -1 means read the whole
                       file
        :type length: int
        :returns: files/read.json response
        :rtype: dict

        """

        url = self.slave_url(slave_id,
                             private_url,
                             'files/read.json')
        params = {'path': path,
                  'length': length,
                  'offset': offset}
        return http.get(url, params=params, timeout=self._timeout).json()

    def master_file_read(self, path, length, offset):
        """This endpoint isn't well documented anywhere, so here is the spec
        derived from the mesos source code:

        request format:
        {
            path: absolute path to read
            offset: start byte location, or -1.  -1 means read no data, and
                    is used to fetch the size of the file in the response's
                    'offset' parameter.
            length: number of bytes to read, or -1.  -1 means read the whole
                    file.
        }

        response format:
        {
            data: file data.  Empty if a request.offset=-1.  Could be
                  smaller than request.length if EOF was reached, or if (I
                  believe) request.length is larger than the length
                  supported by the server (16 pages I believe).

            offset: the offset value from the request, or the size of the
                    file if the request offset was -1 or >= the file size.
        }

        :param path: absolute path to read
        :type path: str
        :param offset: start byte location, or -1.  -1 means read no data, and
                       is used to fetch the size of the file in the response's
                       'offset' parameter.
        :type offset: int
        :param length: number of bytes to read, or -1.  -1 means read the whole
                       file
        :type length: int
        :returns: files/read.json response
        :rtype: dict
        """

        url = self.master_url('files/read.json')
        params = {'path': path,
                  'length': length,
                  'offset': offset}
        return http.get(url, params=params, timeout=self._timeout).json()

    def shutdown_framework(self, framework_id):
        """Shuts down a Mesos framework

        :param framework_id: ID of the framework to shutdown
        :type framework_id: str
        :returns: None
        """

        logger.info('Shutting down framework {}'.format(framework_id))

        data = 'frameworkId={}'.format(framework_id)

        url = self.master_url('master/teardown')

        # In Mesos 0.24, /shutdown was removed.
        # If /teardown doesn't exist, we try /shutdown.
        try:
            http.post(url, data=data, timeout=self._timeout)
        except DCOSHTTPException as e:
            if e.response.status_code == 404:
                url = self.master_url('master/shutdown')
                http.post(url, data=data, timeout=self._timeout)
            else:
                raise

    def metadata(self):
        """ GET /metadata

        :returns: /metadata content
        :rtype: dict
        """
        url = self.get_dcos_url('metadata')
        return http.get(url, timeout=self._timeout).json()

    def browse(self, slave, path):
        """ GET /files/browse.json

        Request
        path:...  # path to run ls on

        Response
        [
          {
            path:  # full path to file
            nlink:
            size:
            mtime:
            mode:
            uid:
            gid:
          }
        ]

        :param slave: slave to issue the request on
        :type slave: Slave
        :returns: /files/browse.json response
        :rtype: dict
        """

        url = self.slave_url(slave['id'],
                             slave.http_url(),
                             'files/browse.json')
        return http.get(url, params={'path': path}).json()


class MesosDNSClient(object):
    """ Mesos-DNS client

    :param url: mesos-dns URL
    :type url: str
    """
    def __init__(self, url=None):
        self.url = url or urllib.parse.urljoin(
            config.get_config_val('core.dcos_url'), '/mesos_dns/')

    def _path(self, path):
        """ Construct a full path

        :param path: path suffix
        :type path: str
        :returns: full path
        :rtype: str
        """
        return urllib.parse.urljoin(self.url, path)

    def hosts(self, host):
        """ GET v1/hosts/<host>

        :param host: host
        :type host: str
        :returns: {'ip', 'host'} dictionary
        :rtype: dict(str, str)
        """
        url = self._path('v1/hosts/{}'.format(host))
        return http.get(url, headers={}).json()


class Master(object):
    """Mesos Master Model

    :param state: Mesos master's state.json
    :type state: dict
    """

    def __init__(self, state):
        self._state = state
        self._frameworks = {}
        self._slaves = {}

    def state(self):
        """Returns master's master/state.json.

        :returns: state.json
        :rtype: dict
        """

        return self._state

    def slave_base_url(self, slave):
        """Returns the base url of the provided slave object.

        :param slave: slave to create a url for
        :type slave: Slave
        :returns: slave's base url
        :rtype: str
        """
        if self._mesos_master_url is not None:
            slave_ip = slave['pid'].split('@')[1]
            return 'http://{}'.format(slave_ip)
        else:
            return urllib.parse.urljoin(self._dcos_url,
                                        'slave/{}/'.format(slave['id']))

    def slave(self, fltr):
        """Returns the slave that has `fltr` in its ID. If any slaves
        are an exact match, returns that task, id not raises a
        DCOSException if there is not exactly one such slave.

        :param fltr: filter string
        :type fltr: str
        :returns: the slave that has `fltr` in its ID
        :rtype: Slave
        """

        slaves = self.slaves(fltr)

        if len(slaves) == 0:
            raise DCOSException('No slave found with ID "{}".'.format(fltr))

        elif len(slaves) > 1:

            exact_matches = [s for s in slaves if s['id'] == fltr]
            if len(exact_matches) == 1:
                return exact_matches[0]

            else:
                matches = ['\t{0}'.format(s['id']) for s in slaves]
                raise DCOSException(
                    "There are multiple slaves with that ID. " +
                    "Please choose one:\n{}".format('\n'.join(matches)))

        else:
            return slaves[0]

    def task(self, fltr, completed=False):
        """Returns the task with `fltr` in its ID.  Raises a DCOSException if
        there is not exactly one such task.

        :param fltr: filter string
        :type fltr: str
        :returns: the task that has `fltr` in its ID
        :param completed: also include completed tasks
        :type completed: bool
        :rtype: Task
        """

        tasks = self.tasks(fltr, completed)

        if len(tasks) == 0:
            raise DCOSException(
                'Cannot find a task with ID containing "{}"'.format(fltr))

        elif len(tasks) > 1:
            msg = [("There are multiple tasks with ID matching [{}]. " +
                    "Please choose one:").format(fltr)]
            msg += ["\t{0}".format(t["id"]) for t in tasks]
            raise DCOSException('\n'.join(msg))

        else:
            return tasks[0]

    def framework(self, framework_id):
        """Returns a framework by ID

        :param framework_id: the framework's ID
        :type framework_id: str
        :returns: the framework
        :rtype: Framework
        """

        for f in self._framework_dicts(True, True):
            if f['id'] == framework_id:
                return self._framework_obj(f)
        return None

    def slaves(self, fltr=""):
        """Returns those slaves that have `fltr` in their 'id'

        :param fltr: filter string
        :type fltr: str
        :returns: Those slaves that have `fltr` in their 'id'
        :rtype: [Slave]
        """

        return [self._slave_obj(slave)
                for slave in self.state()['slaves']
                if fltr in slave['id']]

    def tasks(self, fltr=None, completed=False):
        """Returns tasks running under the master

        :param fltr: May be None, a substring or regex. None returns all tasks,
                     else return tasks whose 'id' matches `fltr`.
        :type fltr: str | None
        :param completed: also include completed tasks
        :type completed: bool
        :returns: a list of tasks
        :rtype: [Task]
        """

        keys = ['tasks']
        if completed:
            keys.extend(['completed_tasks'])

        tasks = []
        for framework in self._framework_dicts(completed, completed):
            for task in _merge(framework, keys):
                if fltr is None or \
                        fltr in task['id'] or \
                        fnmatch.fnmatchcase(task['id'], fltr):
                    task = self._framework_obj(framework).task(task['id'])
                    tasks.append(task)

        return tasks

    # TODO: Currently waiting on this mapping in state.json to be present.
    def get_container_id(self, fltr=None):
        """Returns the container ID for a task ID matching `fltr`

        :param fltr: The task ID which will be mapped to container ID
        :type fltr: str | None
        :returns: the container id associated with task id
        :rtype: str
        """
        return 'foo-container-id'

    def frameworks(self, inactive=False, completed=False):
        """Returns a list of all frameworks

        :param inactive: also include inactive frameworks
        :type inactive: bool
        :param completed: also include completed frameworks
        :type completed: bool
        :returns: a list of frameworks
        :rtype: [Framework]
        """

        return [self._framework_obj(framework)
                for framework in self._framework_dicts(inactive, completed)]

    @util.duration
    def fetch(self, path, **kwargs):
        """GET the resource located at `path`

        :param path: the URL path
        :type path: str
        :param **kwargs: http.get kwargs
        :type **kwargs: dict
        :returns: the response object
        :rtype: Response
        """

        url = urllib.parse.urljoin(self._base_url(), path)
        return http.get(url, **kwargs)

    def _slave_obj(self, slave):
        """Returns the Slave object corresponding to the provided `slave`
        dict.  Creates it if it doesn't exist already.

        :param slave: slave
        :type slave: dict
        :returns: Slave
        :rtype: Slave
        """

        if slave['id'] not in self._slaves:
            self._slaves[slave['id']] = Slave(slave, None, self)
        return self._slaves[slave['id']]

    def _framework_obj(self, framework):
        """Returns the Framework object corresponding to the provided `framework`
        dict.  Creates it if it doesn't exist already.

        :param framework: framework
        :type framework: dict
        :returns: Framework
        :rtype: Framework
        """

        if framework['id'] not in self._frameworks:
            self._frameworks[framework['id']] = Framework(framework, self)
        return self._frameworks[framework['id']]

    def _framework_dicts(self, inactive=False, completed=False):
        """Returns a list of all frameworks as their raw dictionaries

        :param inactive: also include inactive frameworks
        :type inactive: bool
        :param completed: also include completed frameworks
        :type completed: bool
        :returns: a list of frameworks
        """

        if completed:
            for framework in self.state()['completed_frameworks']:
                yield framework

        for framework in self.state()['frameworks']:
            if inactive or framework['active']:
                yield framework


class Slave(object):
    """Mesos Slave Model

    :param short_state: slave's entry from the master's state.json
    :type short_state: dict
    :param state: slave's state.json
    :type state: dict | None
    :param master: slave's master
    :type master: Master
    """

    def __init__(self, short_state, state, master):
        self._short_state = short_state
        self._state = state
        self._master = master

    def state(self):
        """Get the slave's state.json object.  Fetch it if it's not already
        an instance variable.

        :returns: This slave's state.json object
        :rtype: dict
        """

        if not self._state:
            self._state = DCOSClient().get_slave_state(self['id'],
                                                       self.http_url())
        return self._state

    def http_url(self):
        """
        :returns: The private HTTP URL of the slave.  Derived from the
                  `pid` property.
        :rtype: str
        """

        parsed_pid = parse_pid(self['pid'])
        return 'http://{}:{}'.format(parsed_pid[1], parsed_pid[2])

    def _framework_dicts(self):
        """Returns the framework dictionaries from the state.json dict

        :returns: frameworks
        :rtype: [dict]
        """

        return _merge(self.state(), ['frameworks', 'completed_frameworks'])

    def executor_dicts(self):
        """Returns the executor dictionaries from the state.json

        :returns: executors
        :rtype: [dict]
        """

        iters = [_merge(framework, ['executors', 'completed_executors'])
                 for framework in self._framework_dicts()]
        return itertools.chain(*iters)

    def __getitem__(self, name):
        """Support the slave[attr] syntax

        :param name: attribute to get
        :type name: str
        :returns: the value for this attribute in the underlying
                  slave dictionary
        :rtype: object
        """

        return self._short_state[name]


class Framework(object):
    """ Mesos Framework Model

    :param framework: framework properties
    :type framework: dict
    :param master: framework's master
    :type master: Master
    """

    def __init__(self, framework, master):
        self._framework = framework
        self._master = master
        self._tasks = {}  # id->Task map

    def task(self, task_id):
        """Returns a task by id

        :param task_id: the task's id
        :type task_id: str
        :returns: the task
        :rtype: Task
        """

        for task in _merge(self._framework, ['tasks', 'completed_tasks']):
            if task['id'] == task_id:
                return self._task_obj(task)
        return None

    def _task_obj(self, task):
        """Returns the Task object corresponding to the provided `task`
        dict.  Creates it if it doesn't exist already.

        :param task: task
        :type task: dict
        :returns: Task
        :rtype: Task
        """

        if task['id'] not in self._tasks:
            self._tasks[task['id']] = Task(task, self._master)
        return self._tasks[task['id']]

    def dict(self):
        return self._framework

    def __getitem__(self, name):
        """Support the framework[attr] syntax

        :param name: attribute to get
        :type name: str
        :returns: the value for this attribute in the underlying
                  framework dictionary
        :rtype: object
        """

        return self._framework[name]


class Task(object):
    """Mesos Task Model.

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
        """Returns this task's framework

        :returns: task's framework
        :rtype: Framework
        """

        return self._master.framework(self["framework_id"])

    def slave(self):
        """Returns the task's slave

        :returns: task's slave
        :rtype: Slave
        """

        return self._master.slave(self["slave_id"])

    def user(self):
        """Task owner

        :returns: task owner
        :rtype: str
        """

        return self.framework()['user']

    def executor(self):
        """ Returns this tasks' executor

        :returns: task's executor
        :rtype: dict
        """
        for executor in self.slave().executor_dicts():
            tasks = _merge(executor,
                           ['completed_tasks',
                            'tasks',
                            'queued_tasks'])
            if any(task['id'] == self['id'] for task in tasks):
                return executor
        return None

    def directory(self):
        """ Sandbox directory for this task

        :returns: path to task's sandbox
        :rtype: str
        """
        return self.executor()['directory']

    def __getitem__(self, name):
        """Support the task[attr] syntax

        :param name: attribute to get
        :type name: str
        :returns: the value for this attribute in the underlying
                  task dictionary
        :rtype: object
        """

        return self._task[name]


class MesosFile(object):
    """File-like object that is backed by a remote slave or master file.
    Uses the files/read.json endpoint.

    If `task` is provided, the file host is `task.slave()`.  If
    `slave` is provided, the file host is `slave`.  It is invalid to
    provide both.  If neither is provided, the file host is the
    leading master.

    :param path: file's path, relative to the sandbox if `task` is given
    :type path: str
    :param task: file's task
    :type task: Task | None
    :param slave: slave where the file lives
    :type slave: Slave | None
    :param dcos_client: client to use for network requests
    :type dcos_client: DCOSClient | None

    """

    def __init__(self, path, task=None, slave=None, dcos_client=None):
        if task and slave:
            raise ValueError(
                "You cannot provide both `task` and `slave` " +
                "arguments.  `slave` is understood to be `task.slave()`")

        if slave:
            self._slave = slave
        elif task:
            self._slave = task.slave()
        else:
            self._slave = None

        self._task = task
        self._path = path
        self._dcos_client = dcos_client or DCOSClient()
        self._cursor = 0

    def size(self):
        """Size of the file

        :returns: size of the file
        :rtype: int
        """

        params = self._params(0, offset=-1)
        return self._fetch(params)["offset"]

    def seek(self, offset, whence=os.SEEK_SET):
        """Seek to the provided location in the file.

        :param offset: location to seek to
        :type offset: int
        :param whence: determines whether `offset` represents a
                       location that is absolute, relative to the
                       beginning of the file, or relative to the end
                       of the file
        :type whence: os.SEEK_SET | os.SEEK_CUR | os.SEEK_END
        :returns: None
        :rtype: None
        """

        if whence == os.SEEK_SET:
            self._cursor = 0 + offset
        elif whence == os.SEEK_CUR:
            self._cursor += offset
        elif whence == os.SEEK_END:
            self._cursor = self.size() + offset
        else:
            raise ValueError(
                "Unexpected value for `whence`: {}".format(whence))

    def tell(self):
        """ The current cursor position.

        :returns: the current cursor position
        :rtype: int
        """

        return self._cursor

    def read(self, length=None):
        """Reads up to `length` bytes, or the entire file if `length` is None.

        :param length: number of bytes to read
        :type length: int | None
        :returns: data read
        :rtype: str
        """

        data = ''
        while length is None or length - len(data) > 0:
            chunk_length = -1 if length is None else length - len(data)
            chunk = self._fetch_chunk(chunk_length)
            if chunk == '':
                break
            data += chunk

        return data

    def _host_path(self):
        """ The absolute path to the file on slave.

        :returns: the absolute path to the file on slave
        :rtype: str
        """

        if self._task:
            directory = self._task.directory()
            if directory[-1] == '/':
                return directory + self._path
            else:
                return directory + '/' + self._path
        else:
            return self._path

    def _params(self, length, offset=None):
        """GET parameters to send to files/read.json.  See the MesosFile
        docstring for full information.

        :param length: number of bytes to read
        :type length: int
        :param offset: start location.  if None, will use the location
                       of the current file cursor
        :type offset: int
        :returns: GET parameters
        :rtype: dict
        """

        if offset is None:
            offset = self._cursor

        return {
            'path': self._host_path(),
            'offset': offset,
            'length': length
        }

    def _fetch_chunk(self, length, offset=None):
        """Fetch data from files/read.json

        :param length: number of bytes to fetch
        :type length: int
        :param offset: start location.  If not None, this file's
                       cursor is set to `offset`
        :type offset: int
        :returns: data read
        :rtype: str
        """

        if offset is not None:
            self.seek(offset, os.SEEK_SET)

        params = self._params(length)
        data = self._fetch(params)["data"]
        self.seek(len(data), os.SEEK_CUR)
        return data

    def _fetch(self, params):
        """Fetch data from files/read.json

        :param params: GET parameters
        :type params: dict
        :returns: response dict
        :rtype: dict
        """

        if self._slave:
            return self._dcos_client.slave_file_read(self._slave['id'],
                                                     self._slave.http_url(),
                                                     **params)
        else:
            return self._dcos_client.master_file_read(**params)

    def __str__(self):
        """String representation of the file: <task_id:file_path>

        :returns: string representation of the file
        :rtype: str
        """

        if self._task:
            return "task:{0}:{1}".format(self._task['id'], self._path)
        elif self._slave:
            return "slave:{0}:{1}".format(self._slave['id'], self._path)
        else:
            return "master:{0}".format(self._path)



class TaskIO(object):
    """Object allowing interaction with the Mesos Agent exec functionality.

    :param task: task ID
    :type task: str
    :param cmd: the command to fork inside the container
    :type cmd: str
    :param interactive: Create a third persistant connection for streaming
    STDIN
    :type interactive: bool
    :param pty: Allocate a PTY for the remote process
    :type pty: bool
    """

    def __init__(self, task, interactive, tty, cmd=None):
        if not task:
            raise DCOSException(
                "Must provide <task ID>, example:"
                " `dcos task exec <task ID> <cmd>")

        # Get the ContainerID and Agent URL assciated with
        # the given Task ID.
        client = DCOSClient()
        master = get_master(client)
        container_id = master.get_container_id(task)
        if not container_id:
            raise DCOSException(
                "Container ID for task {} not found.".format(task))

        self.container_id = container_id

        # Get the URL to the agent which is running the task
        task_obj = master.task(task)
        self.agent_url = master.slave_base_url(task_obj.slave())

        self.interactive = interactive
        self.tty = tty

        self.output_queue = Queue()
        self.exit_queue = Queue()

        if interactive:
            self.input_queue = Queue()

    def IORunner(self):
        """IORunner handles running the helper methods in this
        class which enable streaming of STDIN/OUT/ERR back and
        forth between the CLI client and Mesos Agent API
        """
        # If a PTY is present, override SIGWINCH to resize the
        # the window.
        if self.tty:
            signal.signal(signal.SIGWINCH, self._window_resizer)

        if self.interactive:
            # Local input thread
            in_thread = Thread(target=self._input_thread)
            in_thread.daemon = True
            in_thread.start()

            # Remote input thread
            in_stream_thread = Thread(
                target=self._attach_input_stream)
            in_stream_thread.daemon = True
            in_stream_thread.start()

        out_stream_thread = Thread(
            target=self._attach_output_stream)
        out_stream_thread.daemon = True
        out_stream_thread.start()

        out_thread = Thread(
            target=self._output_thread)
        out_thread.daemon = True
        out_thread.start()

    try:
        self.exit_queue.get(block=True, timeout=sys.maxint)
    except KeyboardInterrupt:
        pass

    def _initialize_output_message(self):
        """Decides if this is an `attach` or `exec` on the basis that
        an exec needs a cmd, and an attach does not.

        :rtype: string - JSON value for initializing the output stream
        """
        if cmd:
            init_output_attach_msg = pba.Call()
            init_output_attach_msg.type = pba.Call.LAUNCH_NESTED_CONTAINER_SESSION
            init_output_attach_msg.launch_nested_container_session.container_id.value = "foo-container"  # self.container_id
            init_output_attach_msg.launch_nested_container_session.command.value = "ls"  # self.cmd,
            # TODO(@kevin) Add pty bool to protobuf spec
            # nc_msg.tty_info.value = False  # self.tty
            init_output_attach_msg.launch_nested_container_session.interactive = False  # self.interactive

        else:
            init_output_attach_msg = pba.Call.attach_container_output()
            init_output_attach_msg.type = pba.Call.ATTACH_CONTAINER_OUTPUT
            init_output_attach_msg.container_id = "foo"  # self.container_id

        if not init_output_attach_msg.IsInitialized():
            raise DCOSException("Some values for initializing the remote "
                                "output stream are invalid.")

        return MessageToJson(init_output_attach_msg)

    def _attach_output_stream(self):
        """Sends a request to the Mesos Agent API to attach an
        STDOUT stream to an already running container.
        """
        jsonified_output_attach_msg = self._initialize_output_message()

        req_extra_args = {
            'stream': True,
            'headers': {
                'copntent-type': 'application/json'
            }
        }

        response = http.post(
            self.agent_url,
            jsonified_output_attach_msg,
            req_extra_args)

        for chunk in response.itr_content(chunk_size=None):
            json_response_output_msg = Parse(chunk, pbm.ProcessIO)

            if isinstance(json_response_output_msg, pbm.ProcessIO):
                self.output_queue.put(json_response_output_msg)
            # TODO(@malnick)
            # Should probably elif and raise DCOSException here if the
            # value returned is not ProcessIO? Or do we ignore any none
            # processIO types and continue blindly?

        self.output_queue.join()
        self.exit_queue.put(None)

    def _attach_input_stream(self):
        def _input_streamer():
            init_input_attach_msg = pba.Call.attach_container_input()
            init_input_attach_msg.type = pba.Call.ATTACH_CONTAINER_INPUT
            init_input_attach_msg.container_id = "foo"  # self.container_id
            yield MessageToJson(init_input_attach_msg)

            while True:
                yield self.input_queue.get()

        req_extra_args = {
            'stream': True,
            'headers': {
                'connection': 'keep-alive',
                'content-type': 'application/json',
                'transfer-encoding': 'chunked'}}

        response = http.post(
            self.agent_url,
            _input_streamer(),
            req_extra_args)

        if response.status_code != 200:
            raise DCOSException(
                "Input stream returned a non 200 status code")

    def _input_thread(self):
        # For every read of STDIN, take a line
        for chunk in iter(partial(os.read, sys.stdin.fileno(), 1024), ''):
            # Create a ProcessIO message from proto spec
            input_msg = pbm.ProcessIO()
            input_msg.type = pbm.Data.Type.STDIN
            input_msg.data = chunk
            # Create a JSON object from the message
            jsonified_input_msg = MessageToJson(chunk)
            debug(jsonified_input_msg)
            # Dump input msg to the queue for processing
            self.input_queue.put(jsonified_input_msg)

    def _output_thread(self):
        while True:
            # Get message from output queue
            output_json = self.output_queue.get()
            # Transform from JSON to protobuf message
            processio_msg = pbm.ProcessIO()
            output_msg = Parse(output_json, processio_msg)

            if isinstance(output_msg, pbm.ProcessIO.type.STDOUT):
                sys.stdout.write(output_msg.data)
            elif isinstance(output_msg, pbm.ProcessIO.type.STDERR):
                sys.stderr.write(output_msg.data)

            # Close queue assuming last msg was EOF
            self.output_queue.task_done()

    def _window_resizer(self):
        rows, columns = os.popen('stty size', 'r').read().split()

        window_msg = pba.TtyInfo.WindowSize(
            rows,
            columns)

        # resize_me_msg = agent_pb2.Call.LaunchNestedContainerSession.TtyInfo(
        #    AttachContainerMessage.CONTROL_MSG,
        #    control_msg)

        self.input_queue.put(pickle.dumps(window_msg))


def debug(msg):
    print("MSG: {}".format(msg))


def parse_pid(pid):
    """ Parse the mesos pid string,

    :param pid: pid of the form "id@ip:port"
    :type pid: str
    :returns: (id, ip, port)
    :rtype: (str, str, str)
    """

    id_, second = pid.split('@')
    ip, port = second.split(':')
    return id_, ip, port


def _merge(d, keys):
    """ Merge multiple lists from a dictionary into one iterator.
        e.g. _merge({'a': [1, 2], 'b': [3]}, ['a', 'b']) ->
             iter(1, 2, 3)

    :param d: dictionary
    :type d: dict
    :param keys: keys to merge
    :type keys: [hashable]
    :returns: iterator
    :rtype: iter
    """

    return itertools.chain(*[d[k] for k in keys])
