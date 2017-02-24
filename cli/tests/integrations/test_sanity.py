import json

from .helpers.common import (assert_command, delete_zk_nodes, exec_command,
                             file_json, file_json_ast)
from .helpers.marathon import (app, group, pod, show_app, show_group,
                               show_pod, start_app, watch_all_deployments)
from .helpers.package import (package, setup_universe_server,
                              teardown_universe_server)
from .helpers.service import get_services, wait_for_service


def setup_module(module):
    setup_universe_server()


def teardown_module(module):
    teardown_universe_server()
    delete_zk_nodes()


_ZERO_INSTANCE_APP = 'tests/data/marathon/apps/zero_instance_sleep.json'


def test_add_app():
    app_id = 'zero-instance-app'
    with app(_ZERO_INSTANCE_APP, app_id):
        show_app('zero-instance-app')


def test_restarting_app():
    app_id = 'zero-instance-app'
    with app(_ZERO_INSTANCE_APP, app_id):
        start_app(app_id, 3)
        watch_all_deployments()
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'restart', app_id])

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''


def test_add_group():
    group_id = 'test-group'
    with group('tests/data/marathon/groups/good.json', group_id):
        show_group(group_id)


def test_update_group():
    group_app = 'tests/data/marathon/groups/good.json'
    with group(group_app, 'test-group'):
        newapp = json.dumps([{"id": "appadded", "cmd": "sleep 0"}])
        appjson = "apps={}".format(newapp)
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'update', 'test-group/sleep',
                appjson])

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''

        watch_all_deployments()
        show_app('test-group/sleep/appadded')


def test_add_pod():
    pod_id = 'good-pod'
    with pod('tests/data/marathon/pods/good.json', pod_id):
        expected = file_json_ast('tests/data/marathon/pods/good_status.json')
        show_pod(pod_id, expected)


def test_repo_list():
    repo_list = file_json(
        'tests/data/package/json/test_repo_list.json')
    assert_command(
        ['dcos', 'package', 'repo', 'list', '--json'], stdout=repo_list)


def test_package_describe():
    stdout = file_json(
        'tests/data/package/json/test_describe_marathon.json')

    returncode_, stdout_, stderr_ = exec_command(
        ['dcos', 'package', 'describe', 'marathon'])

    assert returncode_ == 0
    output = json.loads(stdout_.decode('utf-8'))
    assert output == json.loads(stdout.decode('utf-8'))
    assert stderr_ == b''


def test_install():
    with package('chronos', deploy=True, args=[]):
        watch_all_deployments()
        wait_for_service('chronos')

    services = get_services(args=['--inactive'])
    assert len([service for service in services
                if service['name'] == 'chronos']) == 0
