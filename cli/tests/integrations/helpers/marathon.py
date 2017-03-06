import contextlib
import json
import re

from .common import assert_command, exec_command


def add_app(app_path, wait=True):
    """ Add an app, and wait for it to deploy

    :param app_path: path to app's json definition
    :type app_path: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    cmd = ['dcos', 'marathon', 'app', 'add', app_path]
    returncode, stdout, stderr = exec_command(cmd)
    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

    if wait:
        watch_all_deployments()


def start_app(app_id, instances=None):
    cmd = ['dcos', 'marathon', 'app', 'start', app_id]
    if instances is not None:
        cmd.append(str(instances))

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''


def list_apps(app_id=None):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list', '--json'])

    result = json.loads(stdout.decode('utf-8'))

    if app_id is None:
        assert len(result) == 0
    else:
        assert len(result) == 1
        assert result[0]['id'] == '/' + app_id

    assert returncode == 0
    assert stderr == b''

    return result


def remove_group(group_id):
    assert_command(['dcos', 'marathon', 'group', 'remove', group_id])

    # Let's make sure that we don't return until the deployment has finished
    watch_all_deployments()


def remove_app(app_id):
    """ Remove an app

    :param app_id: id of app to remove
    :type app_id: str
    :rtype: None
    """

    assert_command(['dcos', 'marathon', 'app', 'remove', '--force', app_id])


def show_group(group_id, version=None):
    if version is None:
        cmd = ['dcos', 'marathon', 'group', 'show', group_id]
    else:
        cmd = ['dcos', 'marathon', 'group', 'show',
               '--group-version={}'.format(version), group_id]

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, dict)
    assert result['id'] == '/' + group_id
    assert stderr == b''

    return result


def remove_pod(pod_id, force=True):
    """ Remove a pod

    :param pod_id: id of app to remove
    :type pod_id: str
    :param force: whether to force a remove
    :type force: bool
    :rtype: None
    """

    cmd = ['dcos', 'marathon', 'pod', 'remove', pod_id]
    if force:
        cmd += ['--force']
    assert_command(cmd)


def show_app(app_id, version=None):
    """Show details of a Marathon application.

    :param app_id: The id for the application
    :type app_id: str
    :param version: The version, either absolute (date-time) or relative
    :type version: str
    :returns: The requested Marathon application
    :rtype: dict
    """

    if version is None:
        cmd = ['dcos', 'marathon', 'app', 'show', app_id]
    else:
        cmd = ['dcos', 'marathon', 'app', 'show',
               '--app-version={}'.format(version), app_id]

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert isinstance(result, dict)
    assert result['id'] == '/' + app_id

    return result


@contextlib.contextmanager
def app(path, app_id, wait=True):
    """Context manager that deploys an app on entrance, and removes it on
    exit.

    :param path: path to app's json definition:
    :type path: str
    :param app_id: app id
    :type app_id: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    add_app(path, wait)
    try:
        yield
    finally:
        remove_app(app_id)
        watch_all_deployments()


def add_pod(pod_path, wait=True):
    """Add a pod, and wait for it to deploy

    :param pod_path: path to pod's json definition
    :type pod_path: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    cmd = ['dcos', 'marathon', 'pod', 'add', pod_path]
    returncode, stdout, stderr = exec_command(cmd)
    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

    if wait:
        watch_all_deployments()


def pod_spec_json(expected_pod_spec, actual_pod_spec):
    """Checks that the "actual" pod spec JSON matches the "expected" JSON.

    The comparison only looks at specific fields that are present in the
    test data used by this module.

    :param expected_pod_spec: contains the baseline values for the comparison
    :type expected_pod_spec: {}
    :param actual_pod_spec: has its fields checked against the expected fields
    :type actual_pod_spec: {}
    :rtype: None
    """

    expected_containers = expected_pod_spec['containers']
    actual_containers = actual_pod_spec['containers']
    actual_containers_by_name = {c['name']: c for c in actual_containers}

    for expected_container in expected_containers:
        container_name = expected_container['name']
        actual_container = actual_containers_by_name[container_name]

        for k, v in expected_container['resources'].items():
            assert actual_container['resources'][k] == v

    assert len(actual_containers) == len(expected_containers)


def pod_status_json(expected_pod_status, actual_pod_status):
    """Checks that the "actual" pod status JSON matched the "expected" JSON.

    The comparison only looks at specific fields that are present in the
    test data used by this module.

    :param expected_pod_status: contains the baseline values for the comparison
    :type expected_pod_status: {}
    :param actual_pod_status: has its fields checked against expected's fields
    :type actual_pod_status: {}
    :rtype: None
    """

    assert actual_pod_status['id'] == expected_pod_status['id']
    assert actual_pod_status['status'] == expected_pod_status['status']
    assert len(actual_pod_status['instances']) == \
        len(expected_pod_status['instances'])

    pod_spec_json(expected_pod_status['spec'],
                  actual_pod_status['spec'])

    expected_instance = expected_pod_status['instances'][0]
    expected_container_statuses = {container['name']: container['status']
                                   for container
                                   in expected_instance['containers']}

    for actual_instance in actual_pod_status['instances']:
        assert actual_instance['status'] == expected_instance['status']

        actual_container_statuses = {container['name']: container['status']
                                     for container
                                     in actual_instance['containers']}

        assert actual_container_statuses == expected_container_statuses


def show_pod(pod_id, expected_json):
    """Show details of a Marathon pod and make sure it matches expected output

    :param pod_id: The id for the pod
    :type pod_id: str
    :param expected_json: expected results for pod `show`
    :type expected_json: dict
    :rtype: None
    """

    cmd = ['dcos', 'marathon', 'pod', 'show', pod_id]
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    status_json = json.loads(stdout.decode('utf-8'))
    pod_status_json(expected_json, status_json)


def add_group(group_path, wait=True):
    """Add a group, and wait for it to deploy

    :param group_path: path to pod's json definition
    :type group_path: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    cmd = ['dcos', 'marathon', 'group', 'add', group_path]
    returncode, stdout, stderr = exec_command(cmd)
    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

    if wait:
        watch_all_deployments()


@contextlib.contextmanager
def group(path, group_id, wait=True):
    """Context manager that deploys an group on entrance, and removes it on exit

    :param path: path to group's json definition:
    :type path: str
    :param group_id: group id
    :type group_id: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    add_group(path, wait)
    try:
        yield
    finally:
        remove_group(group_id)
        watch_all_deployments()


@contextlib.contextmanager
def pod(path, pod_id, wait=True):
    """Context manager that deploys an pod on entrance, and removes it on exit

    :param path: path to pod's json definition:
    :type path: str
    :param pod_id: pod id
    :type pod_id: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    add_pod(path, wait)
    try:
        yield
    finally:
        remove_pod(pod_id)
        watch_all_deployments()


@contextlib.contextmanager
def pods(pods):
    """Context manager that deploys pods on entrance, and removes
    them on exit.

    :param pods: dict of path/to/pod/json -> pod id
    :type pods: {}
    :rtype: None
    """

    for pod_path in pods:
        add_pod(pod_path, wait=False)
    watch_all_deployments()

    try:
        yield
    finally:
        for pod_id in list(pods.values()):
            remove_pod(pod_id)
        watch_all_deployments()


def watch_deployment(deployment_id, count):
    """Wait for a deployment to complete.

    :param deployment_id: deployment id
    :type deployment_id: str
    :param count: max number of seconds to wait
    :type count: int
    :rtype: None
    """

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'deployment', 'watch',
            '--max-count={}'.format(count), deployment_id])

    assert returncode == 0
    assert stderr == b''


def watch_all_deployments(count=300):
    """Wait for all deployments to complete.

    :param count: max number of seconds to wait
    :type count: int
    :rtype: None
    """

    deps = list_deployments()
    for dep in deps:
        watch_deployment(dep['id'], count)


def list_deployments(expected_count=None, app_id=None):
    """Get all active deployments.

    :param expected_count: assert that number of active deployments
    equals `expected_count`
    :type expected_count: int
    :param app_id: only get deployments for this app
    :type app_id: str
    :returns: active deployments
    :rtype: [dict]
    """

    cmd = ['dcos', 'marathon', 'deployment', 'list', '--json']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    if expected_count is not None:
        assert len(result) == expected_count
    assert stderr == b''

    return result
