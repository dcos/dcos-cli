import copy
import datetime
import operator
import posixpath

import textwrap

from collections import OrderedDict

import dateutil.parser
import prettytable

from dcos import auth, marathon, mesos, util

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
        ("HOST", lambda t: _hostname(t)),
        ("USER", lambda t: t.user()),
        ("STATE", lambda t: t["state"].split("_")[-1][0]),
        ("ID", lambda t: t["id"]),
        ("MESOS ID", lambda t: t["slave_id"]),
        ("REGION",
            lambda t: util.get_fault_domain(t.slave())[0] or EMPTY_ENTRY),
        ("ZONE", lambda t: util.get_fault_domain(t.slave())[1] or EMPTY_ENTRY),
    ])

    tb = table(fields, tasks, sortby="NAME")
    tb.align["NAME"] = "l"
    tb.align["HOST"] = "l"
    tb.align["ID"] = "l"
    tb.align["MESOS ID"] = "l"

    return tb


def _hostname(task):
    if task.slave() is None:
        return EMPTY_ENTRY
    else:
        return task.slave()["hostname"]


def app_table(apps, deployments):
    """Returns a PrettyTable representation of the provided apps.

    :param apps: apps to render
    :type apps: [dict]
    :param deployments: deployments to enhance information
    :type deployments: [dict]
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
        ("WAITING", lambda app: app.get('overdue', False)),
        ("CONTAINER", get_container),
        ("CMD", get_cmd)
    ])

    limits = {
        "CMD": 35
    }

    tb = truncate_table(fields, apps, limits, sortby="ID")
    tb.align["CMD"] = "l"
    tb.align["ID"] = "l"
    tb.align["WAITING"] = "l"

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
        ('Status', lambda s: _job_status(s)),
        ('Last Run', lambda s: _last_run_status(s)),
    ])

    tb = truncate_table(fields, job_list, None, sortby="ID")
    tb.align["STATUS"] = 'l'
    tb.align["LAST RUN"] = 'l'

    return tb


def plugins_table(plugin_list):
    """Returns a PrettyTable representation of the plugins list from Marathon.

    :param plugin_list: plugins to render
    :type plugin_list: [plugin]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('id', lambda s: s['id']),
        ('Implementation', lambda s: s['implementation']),
        ('Plugin', lambda s: s['plugin']),
    ])

    tb = truncate_table(fields, plugin_list, None, sortby="ID")
    tb.align["ID"] = 'l'
    tb.align["IMPLEMENTATION"] = 'l'
    tb.align["PLUGIN"] = 'l'

    return tb


def job_history_table(schedule_list):
    """Returns a PrettyTable representation of the job history from Metronome.

    :param schedule_list: job schedule list to render
    :type schedule_list: [history]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('task id', lambda s: s['id']),
        ('started', lambda s: s['createdAt']),
        ('finished', lambda s: s['finishedAt']),
    ])
    tb = table(fields, schedule_list, sortby="FINISHED", reversesort=True)
    tb.align["STARTED"] = 'l'
    tb.align["FINISHED"] = 'l'

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
        ('concurrency policy', lambda s: s['concurrencyPolicy']),
        ('next run', lambda s: s['nextRunAt']),
    ])
    tb = table(fields, schedule_list)
    tb.align['CRON'] = 'l'
    tb.align['ENABLED'] = 'l'
    tb.align['NEXT RUN'] = 'l'
    tb.align['CONCURRENCY POLICY'] = 'l'

    return tb


def job_runs_table(runs_list):
    """Returns a PrettyTable representation of the runs list of a job from
    Metronome.

    :param runs_list: current runs of a job to render
    :type runs_list: [runs]
    :rtype: PrettyTable
    """
    # We expect to receive a list,
    # if not we create one from the single item.
    if not isinstance(runs_list, (list,)):
        runs_list = [runs_list]

    fields = OrderedDict([
        ('task id', lambda s: s['id']),
        ('job id', lambda s: s['jobId']),
        ('started at', lambda s: s['createdAt']),
    ])
    tb = table(fields, runs_list)
    tb.align['JOB ID'] = 'l'
    tb.align['STARTED AT'] = 'l'

    return tb


def _str_to_datetime(datetime_str):
    """ Takes a JSON date of `2017-03-30T15:50:16.187+0000` format and
    Returns a datetime.

    :param datetime_str: JSON date
    :type datetime_str: str
    :rtype: datetime
    """
    if not datetime_str:
        return None
    # Used to parse ISO 8601 formatted date strings.
    return dateutil.parser.parse(datetime_str)


def _last_run_status(job):
    """ Provided a job with embedded history it Returns a status based on the
    following rules:
        0 Runs = 'N/A'
        last success is > last failure = 'Success' otherwise 'Failed'

    :param job: JSON job with embedded history
    :type job: dict
    :rtype: str
    """
    last_success = _str_to_datetime(job['historySummary']['lastSuccessAt'])
    last_failure = _str_to_datetime(job['historySummary']['lastFailureAt'])
    if not last_success and not last_failure:
        return 'N/A'
    elif ((last_success and not last_failure) or
          (last_success and last_success > last_failure)):
        return 'Success'
    else:
        return 'Failed'


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
        ('STATUS SINCE', lambda pod: pod['statusSince']),
        ('WAITING', lambda pod: pod.get('overdue', False))
    ])

    tb = table(fields, pods, sortby=key_column)
    tb.align[key_column] = 'l'
    tb.align['VERSION'] = 'l'
    tb.align['STATUS'] = 'l'
    tb.align['STATUS SINCE'] = 'l'
    tb.align['WAITING'] = 'l'

    return tb


def queued_apps_table(queued_apps):
    """Returns a PrettyTable representation of the Marathon
    launch queue content.

    :param queued_apps: apps to render
    :type queued_apps: [dict]
    :rtype: PrettyTable
    """

    def extract_value_from_entry(entry, value):
        """Extracts the value parameter from given row entry. If value
        is not present, EMPTY_ENTRY will be returned

        :param entry: row entry
        :type entry: [dict]
        :param value: value which should be extracted
        :type value: string
        :rtype: str
        """
        return entry.get('processedOffersSummary', {}).get(value, EMPTY_ENTRY)

    key_column = 'ID'
    fields = OrderedDict([
        (key_column, lambda entry: marathon.get_app_or_pod_id(entry)),
        ('SINCE', lambda entry:
            entry.get('since', EMPTY_ENTRY)
         ),
        ('INSTANCES TO LAUNCH', lambda entry:
            entry.get('count', EMPTY_ENTRY)
         ),
        ('WAITING', lambda entry:
            entry.get('delay', {}).get('overdue', EMPTY_ENTRY)
         ),
        ('PROCESSED OFFERS', lambda entry:
            extract_value_from_entry(entry, 'processedOffersCount')
         ),
        ('UNUSED OFFERS', lambda entry:
            extract_value_from_entry(entry, 'unusedOffersCount')
         ),
        ('LAST UNUSED OFFER', lambda entry:
            extract_value_from_entry(entry, 'lastUnusedOfferAt')
         ),
        ('LAST USED OFFER', lambda entry:
            extract_value_from_entry(entry, 'lastUsedOfferAt')
         ),
    ])

    tb = table(fields, queued_apps, sortby=key_column)
    tb.align[key_column] = 'l'
    tb.align['SINCE'] = 'l'
    tb.align['INSTANCES TO LAUNCH'] = 'l'
    tb.align['WAITING'] = 'l'
    tb.align['PROCESSED OFFERS'] = 'l'
    tb.align['UNUSED OFFERS'] = 'l'
    tb.align['LAST UNUSED OFFER'] = 'l'
    tb.align['LAST USED OFFER'] = 'l'

    return tb


def queued_app_table(queued_app):
    """Returns a PrettyTable representation of the Marathon
    launch queue content.

    :param queued_app: app to render
    :type queued_app: dict
    :rtype: PrettyTable
    """

    def calc_division(dividend, divisor):
        """Calcs divident / divisor, displays 0 if divisor equals 0.

        :param dividend: divident
        :type dividend: int
        :param divisor: divisor
        :type divisor: int
        :rtype: str
        """
        if divisor == 0:
            return 0
        else:
            return 100 * dividend / divisor

    def add_reason_entry(calculations, key, requested, reason_entry):
        """Pretty prints the division of
        reason_entry.get('declined') / reason_entry.get('processed')

        :param calculations: object where result should be added
        :type calculations: dict
        :param key: key for which the result should be added
        :type key: string
        :param requested: the value initially was requested for this entry
        :type requested: string
        :param reason_entry: entry for a declined offer reason
        :type reason_entry: [dict]
        :rtype: str
        """
        dividend = reason_entry.get('processed', 0) - \
            reason_entry.get('declined', 0)
        divisor = reason_entry.get('processed', 0)
        calculations[key]['REQUESTED'] = requested
        calculations[key]['MATCHED'] = '{0} / {1}'\
            .format(dividend, divisor)
        if divisor > 0:
            calculations[key]['PERCENTAGE'] = '{0:0.2f}%' \
                .format(calc_division(dividend, divisor))
        else:
            calculations[key]['PERCENTAGE'] = EMPTY_ENTRY

    def extract_reason_from_list(list, reason_string):
        """Extracts the reason for the given reason_string from the given list

        :param list: list of reason entries
        :type list: [dict]
        :param reason_string: reasong as string
        :type reason_string: str
        :rtype: reason entry
        """
        filtered = [x for x in list if x['reason'] == reason_string]
        if len(filtered) == 1:
            return filtered[0]
        else:
            return {'reason': reason_string, 'declined': 0, 'processed': 0}

    fields = OrderedDict([
        ('RESOURCE', lambda entry:
            calculations.get(entry, {}).get('RESOURCE', EMPTY_ENTRY)
         ),
        ('REQUESTED', lambda entry:
            calculations.get(entry, {}).get('REQUESTED', EMPTY_ENTRY)
         ),
        ('MATCHED', lambda entry:
            calculations.get(entry, {}).get('MATCHED', EMPTY_ENTRY)
         ),
        ('PERCENTAGE', lambda entry:
            calculations.get(entry, {}).get('PERCENTAGE', EMPTY_ENTRY)
         ),
    ])

    summary = queued_app.get('processedOffersSummary', {})
    reasons = summary.get('rejectSummaryLastOffers', {})

    declined_by_role = extract_reason_from_list(
        reasons, 'UnfulfilledRole')
    declined_by_constraints = extract_reason_from_list(
        reasons, 'UnfulfilledConstraint')
    declined_by_cpus = extract_reason_from_list(
        reasons, 'InsufficientCpus')
    declined_by_mem = extract_reason_from_list(
        reasons, 'InsufficientMemory')
    declined_by_disk = extract_reason_from_list(
        reasons, 'InsufficientDisk')
    """declined_by_gpus = extract_reason_from_list(
        reasons, 'InsufficientGpus')"""
    declined_by_ports = extract_reason_from_list(
        reasons, 'InsufficientPorts')

    app = queued_app.get('app')
    if app:
        roles = app.get('acceptedResourceRoles', [])
        if len(roles) == 0:
            spec_roles = '[*]'
        else:
            spec_roles = roles
        spec_constraints = app.get('constraints', EMPTY_ENTRY)
        spec_cpus = app.get('cpus', EMPTY_ENTRY)
        spec_mem = app.get('mem', EMPTY_ENTRY)
        spec_disk = app.get('disk', EMPTY_ENTRY)
        """spec_gpus = app.get('gpus', EMPTY_ENTRY)"""
        spec_ports = app.get('ports', EMPTY_ENTRY)
    else:
        def sum_resources(value):
            def container_value(container):
                return container.get('resources', {}).get(value, 0)

            """While running pods, marathon will add resources for
            the executor to the requested resources.
            Therefore this requirements should be reflected in the summary."""
            def executor_value():
                return pod.get('executorResources', {}).get(value, 0)

            resources = sum(map(container_value, pod.get('containers', [])))
            return resources + executor_value()

        pod = queued_app.get('pod')
        roles = pod.\
            get('scheduling', {}).get('placement', {}).\
            get('acceptedResourceRoles', [])
        if len(roles) == 0:
            spec_roles = '[*]'
        else:
            spec_roles = roles
        spec_constraints = pod.\
            get('scheduling', {}).get('placement', {}).\
            get('constraints', EMPTY_ENTRY)
        spec_cpus = sum_resources('cpus')
        spec_mem = sum_resources('mem')
        spec_disk = sum_resources('disk')
        """spec_gpus = sum_resources('gpus')"""
        spec_ports = []
        for container in pod.get('containers', []):
            for endpoint in container.get('endpoints', []):
                spec_ports.append(endpoint.get('hostPort'))

    """'GPUS'"""
    rows = ['ROLE', 'CONSTRAINTS', 'CPUS', 'MEM', 'DISK', 'PORTS']

    calculations = {}
    for reason in rows:
        calculations[reason] = {}
        calculations[reason]['RESOURCE'] = reason

    add_reason_entry(calculations, 'ROLE', spec_roles, declined_by_role)
    add_reason_entry(
        calculations, 'CONSTRAINTS', spec_constraints,
        declined_by_constraints)
    add_reason_entry(calculations, 'CPUS', spec_cpus, declined_by_cpus)
    add_reason_entry(calculations, 'MEM', spec_mem, declined_by_mem)
    add_reason_entry(calculations, 'DISK', spec_disk, declined_by_disk)
    """
    add_reason_entry(calculations, 'GPUS', spec_gpus, declined_by_gpus)
    """
    add_reason_entry(calculations, 'PORTS', spec_ports, declined_by_ports)

    tb = table(fields, rows)
    tb.align['RESOURCE'] = 'l'
    tb.align['REQUESTED'] = 'l'
    tb.align['MATCHED'] = 'l'
    tb.align['PERCENTAGE'] = 'l'

    return tb


def queued_app_details_table(queued_app):
    """Returns a PrettyTable representation of the Marathon
    launch queue detailed content.

    :param queued_app: app to render
    :type queued_app: dict
    :rtype: PrettyTable
    """

    def value_declined(entry, value):
        """Returns `yes` if the value was inside entry.get('reason'),
        returns `no` otherwise.

        :param entry: row entry
        :type entry: [dict]
        :param value: value which should be checked
        :type value: string
        :rtype: PrettyTable
        """
        if value not in entry.get('reason', []):
            return 'ok'
        else:
            return '-'

    reasons = queued_app.get('lastUnusedOffers')
    fields = OrderedDict([
        ('HOSTNAME', lambda entry:
            entry.get('offer', {}).get('hostname', EMPTY_ENTRY)
         ),
        ('ROLE', lambda entry: value_declined(entry, 'UnfulfilledRole')),
        ('CONSTRAINTS', lambda entry:
            value_declined(entry, 'UnfulfilledConstraint')
         ),
        ('CPUS', lambda entry: value_declined(entry, 'InsufficientCpus')),
        ('MEM', lambda entry: value_declined(entry, 'InsufficientMemory')),
        ('DISK', lambda entry: value_declined(entry, 'InsufficientDisk')),
        ('PORTS', lambda entry: value_declined(entry, 'UnfulfilledRole')),
        ('RECEIVED', lambda entry:
            entry.get('timestamp', EMPTY_ENTRY)
         ),
    ])
    """('GPUS', lambda entry: value_declined(entry, 'InsufficientGpus')),"""

    tb = table(fields, reasons, sortby='HOSTNAME')
    tb.align['HOSTNAME'] = 'l'
    tb.align['REASON'] = 'l'
    tb.align['RECEIVED'] = 'l'

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

    limits = {
        "DESCRIPTION": 65
    }

    tb = truncate_table(fields, packages, limits, sortby="NAME")
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


def auth_provider_table(providers):
    """Returns a PrettyTable representation of the auth providers for cluster

    :param providers: auth providers available
    :type providers: dict
    :rtype: PrettyTable

    """

    fields = OrderedDict([
        ('PROVIDER ID', lambda p: p),
        ('AUTHENTICATION TYPE', lambda p: auth.auth_type_description(
                                            providers[p])),
    ])

    tb = table(fields, providers, sortby="PROVIDER ID")
    tb.align['PROVIDER ID'] = 'l'
    tb.align['AUTHENTICATION TYPE'] = 'l'

    return tb


def clusters_table(clusters):
    """Returns a PrettyTable representation of the configured clusters

    :param clusters: configured clusters
    :type clusters: [Cluster]
    :rtype: PrettyTable
    """

    def print_name(c):
        msg = c['name']
        if c['attached']:
            msg += "*"
        return msg

    fields = OrderedDict([
        ('NAME', lambda c: print_name(c)),
        ('CLUSTER ID', lambda c: c['cluster_id']),
        ('STATUS', lambda c: c['status']),
        ('VERSION', lambda c: c['version']),
        ('URL', lambda c: c['url'] or "N/A")
    ])

    tb = table(fields, clusters, sortby="CLUSTER ID")

    return tb


def node_table(nodes, field_names=()):
    """Returns a PrettyTable representation of the provided DC/OS nodes

    :param nodes: nodes to render.
    :type nodes: [dict]
    :param field_names: Extra fields to add to the table
    :type nodes: [str]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('HOSTNAME', lambda s: s.get('host', s.get('hostname'))),
        ('IP', lambda s: s.get('ip') or mesos.parse_pid(s['pid'])[1]),
        ('ID', lambda s: s['id']),
        ('TYPE', lambda s: s['type']),
        ('REGION', lambda s: s['region']),
        ('ZONE', lambda s: s['zone']),
    ])

    for field_name in field_names:
        if field_name.upper() in fields:
            continue
        if ':' in field_name:
            heading, field_name = field_name.split(':', 1)
        else:
            heading = field_name
        fields[heading.upper()] = _dotted_itemgetter(field_name)

    sortby = list(fields.keys())[0]
    tb = table(fields, nodes, sortby=sortby)
    tb.align['TYPE'] = 'l'
    return tb


def dns_table(nodes, field_names=()):
    """Returns a PrettyTable representation of the provided DC/OS nodes

    :param nodes: nodes to render.
    :type nodes: [dict]
    :param field_names: Extra fields to add to the table
    :type nodes: [str]
    :rtype: PrettyTable
    """

    fields = OrderedDict([
        ('HOST', lambda s: s.get('host')),
        ('IP', lambda s: s.get('ip')),
    ])

    tb = table(fields, nodes)
    tb.align['HOST'] = 'l'
    return tb


def _dotted_itemgetter(field_name):
    """Returns a func that gets the value in a nested dict where the
    `field_name` is a dotted path to the key.

    Example:

      >>> from dcoscli.tables import _dotted_itemgetter
      >>> d1 = {'a': {'b': {'c': 21}}}
      >>> d2 = {'a': {'b': {'c': 22}}}
      >>> func = _dotted_itemgetter('a.b.c')
      >>> func(d1)
      21
      >>> func(d2)
      22

    :param field_name: dotted path to key in nested dict
    :type field_name: str
    :rtype: callable
    """

    if '.' not in field_name:
        return operator.itemgetter(field_name)
    head, tail = field_name.split('.', 1)
    return lambda d: _dotted_itemgetter(tail)(d[head])


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


def metrics_summary_table(data):
    """Prints a table of CPU, Memory and Disk for the given data.

    :param data: A dictionary of formatted summary values.
    :type data: dict
    :rtype: PrettyTable
    """
    fields = OrderedDict([
        ('CPU', lambda d: d['cpu']),
        ('MEM', lambda d: d['mem']),
        ('DISK', lambda d: d['disk'])
    ])

    # table has a single row
    metrics_table = table(fields, [data])
    metrics_table.align['CPU'] = 'l'
    metrics_table.align['MEM'] = 'l'
    metrics_table.align['DISK'] = 'l'

    return metrics_table


def metrics_details_table(datapoints, show_tags=True):
    """Prints a table of all passed metrics

    :param datapoints: A raw list of datapoints
    :type datapoints: [dict]
    :param show_tags: Show column for tags, unless False
    :type show_tags: bool
    :rtype: PrettyTable
    """

    field_defs = [
        ('NAME', lambda d: d['name']),
        ('VALUE', lambda d: d['value']),
    ]
    if show_tags:
        field_defs.append(('TAGS', lambda d: d['tags']))

    fields = OrderedDict(field_defs)

    metrics_table = table(fields, datapoints)
    for (k, v) in field_defs:
        metrics_table.align[k] = 'l'

    return metrics_table


def truncate_table(fields, objs, limits, **kwargs):
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
    :param limits: limits for truncating for each row
    :type limits: [object]
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

    def format_table(obj, key, function):
        """Formats the given object for the given function

        :param object: object to format
        :type object: object
        :param key: value which should be checked
        :type key: string
        :param function: function to format the cell
        :type function: function
        :rtype: PrettyTable
        """
        try:
            result = str(function(obj))
        except KeyError:
            result = 'N/A'
        if (limits is not None and limits.get(key) is not None):
            result = textwrap.\
                shorten(result, width=limits.get(key), placeholder='...')
        return result

    for obj in objs:
        row = [format_table(obj, key, fields.get(key))
               for key in fields.keys()]
        tb.add_row(row)

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

    return truncate_table(fields, objs, None, **kwargs)
