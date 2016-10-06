import copy
import datetime
import posixpath
from collections import OrderedDict

import prettytable
from dcos import mesos, util

EMPTY_ENTRY = '---'

DEPLOYMENT_DISPLAY = {'ResolveArtifacts': 'artifacts',
                      'ScaleApplication': 'scale',
                      'StartApplication': 'start',
                      'StopApplication': 'stop',
                      'RestartApplication': 'restart',
                      'ScalePod': 'scale',
                      'StartPod': 'start',
                      'StopPod': 'stop',
                      'RestartPod': 'restart',
                      'KillAllOldTasksOf': 'kill-tasks'}

logger = util.get_logger(__name__)


def task_table(tasks):
    """Returns a PrettyTable representation of the provided mesos tasks.

    :param tasks: tasks to render
    :type tasks: [Task]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ("NAME", lambda t: t["name"]),
        ("HOST", lambda t: t.slave()["hostname"]),
        ("USER", lambda t: t.user()),
        ("STATE", lambda t: t["state"].split("_")[-1][0]),
        ("ID", lambda t: t["id"]),
    ])

    tb = table(fields, tasks, sortby="NAME")
    tb.align["NAME"] = "l"
    tb.align["HOST"] = "l"
    tb.align["ID"] = "l"

    return tb


def app_table(apps, deployments):
    """Returns a PrettyTable representation of the provided apps.

    :param tasks: apps to render
    :type tasks: [dict]
    :rtype: PrettyTable
    """

    deployment_map = {}
    for deployment in deployments:
        deployment_map[deployment['id']] = deployment

    def get_cmd(app):
        if app["cmd"] is not None:
            return app["cmd"]
        else:
            return app["args"]

    def get_container(app):
        if app["container"] is not None:
            return app["container"]["type"]
        else:
            return "mesos"

    def get_health(app):
        if app["healthChecks"]:
            return "{}/{}".format(app["tasksHealthy"],
                                  app["tasksRunning"])
        else:
            return EMPTY_ENTRY

    def get_deployment(app):
        deployment_ids = {deployment['id']
                          for deployment in app['deployments']}

        actions = []
        for deployment_id in deployment_ids:
            deployment = deployment_map.get(deployment_id)
            if deployment:
                for action in deployment['currentActions']:
                    if action['app'] == app['id']:
                        actions.append(DEPLOYMENT_DISPLAY[action['action']])

        if len(actions) == 0:
            return EMPTY_ENTRY
        elif len(actions) == 1:
            return actions[0]
        else:
            return "({})".format(", ".join(actions))

    fields = OrderedDict([
        ("ID", lambda a: a["id"]),
        ("MEM", lambda a: a["mem"]),
        ("CPUS", lambda a: a["cpus"]),
        ("TASKS", lambda a: "{}/{}".format(a["tasksRunning"],
                                           a["instances"])),
        ("HEALTH", get_health),
        ("DEPLOYMENT", get_deployment),
        ("CONTAINER", get_container),
        ("CMD", get_cmd)
    ])

    tb = table(fields, apps, sortby="ID")
    tb.align["CMD"] = "l"
    tb.align["ID"] = "l"

    return tb


def app_task_table(tasks):
    """Returns a PrettyTable representation of the provided marathon tasks.

    :param tasks: tasks to render
    :type tasks: [dict]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ("APP", lambda t: t["appId"]),
        ("HEALTHY", lambda t:
         all(check['alive'] for check in t.get('healthCheckResults', []))),
        ("STARTED", lambda t: t.get("startedAt", "N/A")),
        ("HOST", lambda t: t["host"]),
        ("ID", lambda t: t["id"])
    ])

    tb = table(fields, tasks, sortby="APP")
    tb.align["APP"] = "l"
    tb.align["ID"] = "l"

    return tb


def deployment_table(deployments):
    """Returns a PrettyTable representation of the provided marathon
    deployments.

    :param deployments: deployments to render
    :type deployments: [dict]
    :rtype: PrettyTable

    """

    def join_path_ids(deployment, affected_resources_key):
        """Create table cell for "affectedApps"/"affectedPods" in deployment.

        :param deployment: the deployment JSON to read
        :type deployment: {}
        :param affected_resources_key: either "affectedApps" or "affectedPods"
        :type affected_resources_key: str
        :returns: newline-separated path IDs if they exist, otherwise an empty
                  cell indicator
        :rtype: str
        """

        path_ids = deployment.get(affected_resources_key)
        return '\n'.join(path_ids) if path_ids else '-'

    def resource_path_id(action):
        """Get the path ID of the app or pod represented by the given action.

        :param action: the Marathon deployment action JSON object to read
        :type action: {}
        :returns: the value of the "app" or "pod" field if it exists, else None
        :rtype: str
        """

        path_id = action.get('app') or action.get('pod')

        if path_id is None:
            template = 'Expected "app" or "pod" field in action: %s'
            logger.exception(template, action)

        return path_id

    def get_action(deployment):

        multiple_resources = len({resource_path_id(action) for action in
                                  deployment['currentActions']}) > 1

        ret = []
        for action in deployment['currentActions']:
            try:
                action_display = DEPLOYMENT_DISPLAY[action['action']]
            except KeyError:
                logger.exception('Missing action entry')

                raise ValueError(
                    'Unknown Marathon action: {}'.format(action['action']))

            if resource_path_id(action) is None:
                ret.append('N/A')
            elif multiple_resources:
                path_id = resource_path_id(action)
                ret.append('{0} {1}'.format(action_display, path_id))
            else:
                ret.append(action_display)

        return '\n'.join(ret)

    fields = OrderedDict([
        ('APP', lambda d: join_path_ids(d, 'affectedApps')),
        ('POD', lambda d: join_path_ids(d, 'affectedPods')),
        ('ACTION', get_action),
        ('PROGRESS', lambda d: '{0}/{1}'.format(d['currentStep']-1,
                                                d['totalSteps'])),
        ('ID', lambda d: d['id'])
    ])

    tb = table(fields, deployments, sortby="APP")
    tb.align['APP'] = 'l'
    tb.align['POD'] = 'l'
    tb.align['ACTION'] = 'l'
    tb.align['ID'] = 'l'

    return tb


def service_table(services):
    """Returns a PrettyTable representation of the provided DC/OS services.

    :param services: services to render
    :type services: [Framework]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ("NAME", lambda s: s['name']),
        ("HOST", lambda s: s['hostname']),
        ("ACTIVE", lambda s: s['active']),
        ("TASKS", lambda s: len(s['tasks'])),
        ("CPU", lambda s: s['resources']['cpus']),
        ("MEM", lambda s: s['resources']['mem']),
        ("DISK", lambda s: s['resources']['disk']),
        ("ID", lambda s: s['id']),
    ])

    tb = table(fields, services, sortby="NAME")
    tb.align["ID"] = 'l'
    tb.align["NAME"] = 'l'

    return tb


def job_table(job_list):
    """Returns a PrettyTable representation of the job list from Metronome.

    :param job_list: jobs to render
    :type job_list: [job]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('id', lambda s: s['id']),
        ('Description', lambda s:
            _truncate_desc(s['description'] if 'description' in s else '')),
        ('Status', lambda s: _job_status(s)),
        ('Last Succesful Run', lambda s: s['history']['lastSuccessAt']
            if 'history' in s else 'N/A'),
    ])
    tb = table(fields, job_list, sortby="ID")
    tb.align['ID'] = 'l'
    tb.align["DESCRIPTION"] = 'l'
    tb.align["STATUS"] = 'l'

    return tb


def job_history_table(schedule_list):
    """Returns a PrettyTable representation of the job history from Metronome.

    :param schedule_list: job schedule list to render
    :type schedule_list: [history]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('id', lambda s: s['id']),
        ('started', lambda s: s['createdAt']),
        ('finished', lambda s: s['finishedAt']),
    ])
    tb = table(fields, schedule_list, sortby="STARTED")
    tb.align['ID'] = 'l'

    return tb


def schedule_table(schedule_list):
    """Returns a PrettyTable representation of the schedule list of a job
    from Metronome.

    :param schedule_list: schedules to render
    :type schedule_list: [schedule]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('id', lambda s: s['id']),
        ('cron', lambda s: s['cron']),
        ('enabled', lambda s: s['enabled']),
        ('next run', lambda s: s['nextRunAt']),
        ('concurrency policy', lambda s: s['concurrencyPolicy']),
    ])
    tb = table(fields, schedule_list)
    tb.align['ID'] = 'l'
    tb.align['CRON'] = 'l'

    return tb


def job_runs_table(runs_list):
    """Returns a PrettyTable representation of the runs list of a job from
    Metronome.

    :param runs_list: current runs of a job to render
    :type runs_list: [runs]
    :rtype: PrettyTable
    """
    fields = OrderedDict([
        ('job id', lambda s: s['jobId']),
        ('id', lambda s: s['id']),
        ('started at', lambda s: s['createdAt']),
    ])
    tb = table(fields, runs_list)
    tb.align['ID'] = 'l'
    tb.align['JOB ID'] = 'l'

    return tb


def _truncate_desc(description, truncation_size=35):
    """Utility function that truncates a string for formatting.

    :param description: description
    :type description: str
    :rtype: str

    """

    if(len(description) > truncation_size):
        return description[:truncation_size] + '..'
    else:
        return description


def _job_status(job):
    """Utility function that returns the status of a job

    :param job: job json
    :type job: json
    :rtype: str

    """

    if 'activeRuns' in job:
        return "Running"
    # short circuit will prevent failure
    elif 'schedules' not in job or not job['schedules']:
        return "Unscheduled"
    else:
        return "Scheduled"


def _count_apps(group, group_dict):
    """Counts how many apps are registered for each group.  Recursively
    populates the profided `group_dict`, which maps group_id ->
    (group, count).

    :param group: nested group dictionary
    :type group: dict
    :param group_dict: group map that maps group_id -> (group, count)
    :type group_dict: dict
    :rtype: dict

    """

    for child_group in group['groups']:
        _count_apps(child_group, group_dict)

    count = (len(group['apps']) +
             sum(group_dict[child_group['id']][1]
                 for child_group in group['groups']))

    group_dict[group['id']] = (group, count)


def group_table(groups):
    """Returns a PrettyTable representation of the provided marathon
    groups

    :param groups: groups to render
    :type groups: [dict]
    :rtype: PrettyTable

    """

    group_dict = {}
    for group in groups:
        _count_apps(group, group_dict)

    fields = OrderedDict([
        ('ID', lambda g: g[0]['id']),
        ('APPS', lambda g: g[1]),
    ])

    tb = table(fields, group_dict.values(), sortby="ID")
    tb.align['ID'] = 'l'

    return tb


def pod_table(pods):
    """Returns a PrettyTable representation of the provided Marathon pods.

    :param pods: pods to render
    :type pods: [dict]
    :rtype: PrettyTable
    """

    def id_and_containers(pod):
        """Extract the pod ID and container names from the given pod JSON.

        :param pod: the pod JSON to read
        :type pod: {}
        :returns: the entry for the ID+CONTAINER column of the pod table
        :rtype: str
        """

        pod_id = pod['id']
        container_names = sorted(container['name'] for container
                                 in pod['spec']['containers'])

        container_lines = ('\n |-{}'.format(name) for name in container_names)
        return pod_id + ''.join(container_lines)

    key_column = 'ID+TASKS'
    fields = OrderedDict([
        (key_column, id_and_containers),
        ('INSTANCES', lambda pod: len(pod.get('instances', []))),
        ('VERSION', lambda pod: pod['spec'].get('version', '-')),
        ('STATUS', lambda pod: pod['status']),
        ('STATUS SINCE', lambda pod: pod['statusSince'])
    ])

    tb = table(fields, pods, sortby=key_column)
    tb.align[key_column] = 'l'
    tb.align['VERSION'] = 'l'
    tb.align['STATUS'] = 'l'
    tb.align['STATUS SINCE'] = 'l'

    return tb


def package_table(packages):
    """Returns a PrettyTable representation of the provided DC/OS packages

    :param packages: packages to render
    :type packages: [dict]
    :rtype: PrettyTable

    """

    fields = OrderedDict([
        ('NAME', lambda p: p['name']),
        ('VERSION', lambda p: p['version']),
        ('APP',
         lambda p: '\n'.join(p['apps']) if p.get('apps') else EMPTY_ENTRY),
        ('COMMAND',
         lambda p: p['command']['name'] if 'command' in p else EMPTY_ENTRY),
        ('DESCRIPTION', lambda p: p['description'])
    ])

    tb = table(fields, packages, sortby="NAME")
    tb.align['NAME'] = 'l'
    tb.align['VERSION'] = 'l'
    tb.align['APP'] = 'l'
    tb.align['COMMAND'] = 'l'
    tb.align['DESCRIPTION'] = 'l'

    return tb


def package_search_table(search_results):
    """Returns a PrettyTable representation of the provided DC/OS package
    search results

    :param search_results: search_results, in the format of
                           dcos.package.IndexEntries::as_dict()
    :type search_results: [dict]
    :rtype: PrettyTable

    """

    fields = OrderedDict([
        ('NAME', lambda p: p['name']),
        ('VERSION', lambda p: p['currentVersion']),
        ('SELECTED', lambda p: p.get("selected", False)),
        ('FRAMEWORK', lambda p: p['framework']),
        ('DESCRIPTION', lambda p: p['description']
            if len(p['description']) < 77 else p['description'][0:77] + "...")
    ])

    packages = []
    for package in search_results['packages']:
        package_ = copy.deepcopy(package)
        packages.append(package_)

    tb = table(fields, packages)
    tb.align['NAME'] = 'l'
    tb.align['VERSION'] = 'l'
    tb.align['SELECTED'] = 'l'
    tb.align['FRAMEWORK'] = 'l'
    tb.align['DESCRIPTION'] = 'l'

    return tb


def slave_table(slaves):
    """Returns a PrettyTable representation of the provided DC/OS slaves

    :param slaves: slaves to render.  dicts from /mesos/state-summary
    :type slaves: [dict]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('HOSTNAME', lambda s: s['hostname']),
        ('IP', lambda s: mesos.parse_pid(s['pid'])[1]),
        ('ID', lambda s: s['id'])
    ])

    tb = table(fields, slaves, sortby="HOSTNAME")
    return tb


def _format_unix_timestamp(ts):
    """ Formats a unix timestamp in a `dcos task ls --long` format.

    :param ts: unix timestamp
    :type ts: int
    :rtype: str
    """
    return datetime.datetime.fromtimestamp(ts).strftime('%b %d %H:%M')


def ls_long_table(files):
    """Returns a PrettyTable representation of `files`

    :param files: Files to render.  Of the form returned from the
        mesos /files/browse.json endpoint.
    :param files: [dict]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('MODE', lambda f: f['mode']),
        ('NLINK', lambda f: f['nlink']),
        ('UID', lambda f: f['uid']),
        ('GID', lambda f: f['gid']),
        ('SIZE', lambda f: f['size']),
        ('DATE', lambda f: _format_unix_timestamp(int(f['mtime']))),
        ('PATH', lambda f: posixpath.basename(f['path']))])

    tb = table(fields, files, sortby="PATH", header=False)
    tb.align = 'r'
    return tb


def table(fields, objs, **kwargs):
    """Returns a PrettyTable.  `fields` represents the header schema of
    the table.  `objs` represents the objects to be rendered into
    rows.

    :param fields: An OrderedDict, where each element represents a
                   column.  The key is the column header, and the
                   value is the function that transforms an element of
                   `objs` into a value for that column.
    :type fields: OrderdDict(str, function)
    :param objs: objects to render into rows
    :type objs: [object]
    :param **kwargs: kwargs to pass to `prettytable.PrettyTable`
    :type **kwargs: dict
    :rtype: PrettyTable
    """

    tb = prettytable.PrettyTable(
        [k.upper() for k in fields.keys()],
        border=False,
        hrules=prettytable.NONE,
        vrules=prettytable.NONE,
        left_padding_width=0,
        right_padding_width=1,
        **kwargs
    )

    # Set these explicitly due to a bug in prettytable where
    # '0' values are not honored.
    tb._left_padding_width = 0
    tb._right_padding_width = 2

    for obj in objs:
        row = [fn(obj) for fn in fields.values()]
        tb.add_row(row)

    return tb
