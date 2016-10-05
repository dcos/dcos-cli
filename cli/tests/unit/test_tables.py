import datetime

import mock
import pytz

from dcos.mesos import Slave
from dcoscli import tables

from ..fixtures.marathon import (app_fixture, app_task_fixture,
                                 deployment_fixture_app_post_pods,
                                 deployment_fixture_app_pre_pods,
                                 deployment_fixture_pod,
                                 group_fixture, pod_list_fixture,
                                 pod_list_without_instances_fixture,
                                 pod_list_without_spec_version_fixture)
from ..fixtures.node import slave_fixture
from ..fixtures.package import package_fixture, search_result_fixture
from ..fixtures.service import framework_fixture
from ..fixtures.task import browse_fixture, task_fixture


def test_task_table():
    task = task_fixture()
    task.user = mock.Mock(return_value='root')
    slave = Slave({"hostname": "mock-hostname"}, None, None)
    task.slave = mock.Mock(return_value=slave)
    _test_table(tables.task_table,
                [task],
                'tests/unit/data/task.txt')


def test_app_table():
    apps = [app_fixture()]
    deployments = []
    table = tables.app_table(apps, deployments)
    with open('tests/unit/data/app.txt') as f:
        assert str(table) == f.read()


def test_deployment_table_app_pre_pods():
    _test_table(tables.deployment_table,
                [deployment_fixture_app_pre_pods()],
                'tests/unit/data/deployment/app.txt')


def test_deployment_table_app_post_pods():
    _test_table(tables.deployment_table,
                [deployment_fixture_app_post_pods()],
                'tests/unit/data/deployment/app.txt')


def test_deployment_table_pod():
    _test_table(tables.deployment_table,
                [deployment_fixture_pod()],
                'tests/unit/data/deployment/pod.txt')


def test_app_task_table():
    _test_table(tables.app_task_table,
                [app_task_fixture()],
                'tests/unit/data/app_task.txt')


def test_service_table():
    _test_table(tables.service_table,
                [framework_fixture()],
                'tests/unit/data/service.txt')


def test_group_table():
    _test_table(tables.group_table,
                [group_fixture()],
                'tests/unit/data/group.txt')


def test_pod_table():
    _test_table(tables.pod_table,
                pod_list_fixture(),
                'tests/unit/data/pod.txt')


def test_pod_table_without_instances():
    _test_table(tables.pod_table,
                [pod_list_without_instances_fixture()],
                'tests/unit/data/pod_without_instances.txt')


def test_pod_table_without_spec_version():
    _test_table(tables.pod_table,
                [pod_list_without_spec_version_fixture()],
                'tests/unit/data/pod_without_spec_version.txt')


def test_package_table():
    _test_table(tables.package_table,
                [package_fixture()],
                'tests/unit/data/package.txt')


def test_package_search_table():
    _test_table(tables.package_search_table,
                search_result_fixture(),
                'tests/unit/data/package_search.txt')


def test_node_table():
    _test_table(tables.slave_table,
                [slave_fixture()],
                'tests/unit/data/node.txt')


def test_ls_long_table():
    with mock.patch('dcoscli.tables._format_unix_timestamp',
                    lambda ts: datetime.datetime.fromtimestamp(
                        ts, pytz.utc).strftime('%b %d %H:%M')):
        _test_table(tables.ls_long_table,
                    browse_fixture(),
                    'tests/unit/data/ls_long.txt')


def _test_table(table_fn, fixture_fn, path):
    table = table_fn(fixture_fn)
    with open(path) as f:
        assert str(table) == f.read()
