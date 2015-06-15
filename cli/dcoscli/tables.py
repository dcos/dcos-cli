import copy
from collections import OrderedDict

from dcos import util


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

    tb = util.table(fields, tasks, sortby="NAME")
    tb.align["NAME"] = "l"
    tb.align["HOST"] = "l"
    tb.align["ID"] = "l"

    return tb


def app_table(apps):
    """Returns a PrettyTable representation of the provided apps.

    :param tasks: apps to render
    :type tasks: [dict]
    :rtype: PrettyTable
    """

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

    fields = OrderedDict([
        ("ID", lambda a: a["id"]),
        ("MEM", lambda a: a["mem"]),
        ("CPUS", lambda a: a["cpus"]),
        ("DEPLOYMENTS", lambda a: len(a["deployments"])),
        ("TASKS", lambda a: "{}/{}".format(a["tasksRunning"],
                                           a["instances"])),
        ("CONTAINER", get_container),
        ("CMD", get_cmd)
    ])

    tb = util.table(fields, apps, sortby="ID")
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
        ("STARTED", lambda t: t["startedAt"]),
        ("HOST", lambda t: t["host"]),
        ("ID", lambda t: t["id"])
    ])

    tb = util.table(fields, tasks, sortby="APP")
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
        action_map = {'ResolveArtifacts': 'artifacts',
                      'ScaleApplication': 'scale',
                      'StartApplication': 'start',
                      'StopApplication': 'stop',
                      'RestartApplication': 'restart',
                      'KillAllOldTasksOf': 'kill-tasks'}

        multiple_apps = len({action['app']
                             for action in deployment['currentActions']}) > 1

        ret = []
        for action in deployment['currentActions']:
            try:
                action_display = action_map[action['action']]
            except KeyError:
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

    tb = util.table(fields, deployments, sortby="APP")
    tb.align['APP'] = 'l'
    tb.align['ACTION'] = 'l'
    tb.align['ID'] = 'l'

    return tb


def service_table(services):
    """Returns a PrettyTable representation of the provided DCOS services.

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

    tb = util.table(fields, services, sortby="NAME")
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

    tb = util.table(fields, group_dict.values(), sortby="ID")
    tb.align['ID'] = 'l'

    return tb


def package_table(packages):
    """Returns a PrettyTable representation of the provided DCOS packages

    :param packages: packages to render
    :type packages: [dict]
    :rtype: PrettyTable

    """

    fields = OrderedDict([
        ('NAME', lambda p: p['name']),
        ('APP', lambda p: '\n'.join(p['apps']) if p.get('apps') else '---'),
        ('COMMAND',
         lambda p: p['command']['name'] if 'command' in p else '---'),
        ('DESCRIPTION', lambda p: p['description'])
    ])

    tb = util.table(fields, packages, sortby="NAME")
    tb.align['NAME'] = 'l'
    tb.align['APP'] = 'l'
    tb.align['COMMAND'] = 'l'
    tb.align['DESCRIPTION'] = 'l'

    return tb


def package_search_table(search_results):
    """Returns a PrettyTable representation of the provided DCOS package
    search results

    :param search_results: search_results, in the format of
                           dcos.package.IndexEntries::as_dict()
    :type search_results: [dict]
    :rtype: PrettyTable

    """

    fields = OrderedDict([
        ('NAME', lambda p: p['name']),
        ('VERSION', lambda p: p['currentVersion']),
        ('FRAMEWORK', lambda p: p['framework']),
        ('SOURCE', lambda p: p['source']),
        ('DESCRIPTION', lambda p: p['description'])
    ])

    packages = []
    for result in search_results:
        for package in result['packages']:
            package_ = copy.deepcopy(package)
            package_['source'] = result['source']
            packages.append(package_)

    tb = util.table(fields, packages, sortby="NAME")
    tb.align['NAME'] = 'l'
    tb.align['VERSION'] = 'l'
    tb.align['FRAMEWORK'] = 'l'
    tb.align['SOURCE'] = 'l'
    tb.align['DESCRIPTION'] = 'l'

    return tb


def cluster_table(components):
    """Returns a PrettyTable representation of the provided DCOS cluster

    :param components: components to render
    :type components: [dict]
    :rtype: PrettyTable

    """

    fields = OrderedDict([
        ('COMPONENT NAME', lambda p: p['Name']),
        ('STATUS', lambda p: p['Status'])
    ])

    tb = util.table(fields, components, sortby="COMPONENT NAME")
    tb.align['COMPONENT NAME'] = 'l'
    tb.align['STATUS'] = 'l'
    return tb
