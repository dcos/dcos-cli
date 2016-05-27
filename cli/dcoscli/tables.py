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

    def get_action(deployment):

        multiple_apps = len({action['app']
                             for action in deployment['currentActions']}) > 1

        ret = []
        for action in deployment['currentActions']:
            try:
                action_display = DEPLOYMENT_DISPLAY[action['action']]
            except KeyError:
                logger.exception('Missing action entry')

                raise ValueError(
                    'Unknown Marathon action: {}'.format(action['action']))

            if multiple_apps:
                ret.append('{0} {1}'.format(action_display, action['app']))
            else:
                ret.append(action_display)

        return '\n'.join(ret)

    fields = OrderedDict([
        ('APP', lambda d: '\n'.join(d['affectedApps'])),
        ('ACTION', get_action),
        ('PROGRESS', lambda d: '{0}/{1}'.format(d['currentStep']-1,
                                                d['totalSteps'])),
        ('ID', lambda d: d['id'])
    ])

    tb = table(fields, deployments, sortby="APP")
    tb.align['APP'] = 'l'
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
