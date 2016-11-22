import contextlib
import os
import pytest

from .common import (app, exec_command, pod)
from .test_marathon import (_list_tasks)

_PODS_ENABLED = 'DCOS_PODS_ENABLED' in os.environ


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_list():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'list'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'OVERDUE' in decoded
        assert '/stuck-sleep' in decoded
        """There should be a line of the following format in the stdout:
        /stuck-sleep $since 9 True 4 3 $last_unsued_offer $last_used_offer
        To avoid formatting issues, whitspaces are ignored.
        Explanation:
        9 Instances should be launched and $since timestamp ends with `Z`.
        """
        assert 'Z9' in decoded.replace(' ', '')


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_list_json():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'list', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'overdue' in decoded
        assert '/stuck-sleep' in decoded
        assert '"reason": "UnfulfilledConstraint"' in decoded


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_list_pod():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'list'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'OVERDUE' in decoded
        assert '/stuck-pod' in decoded
        """There should be a line of the following format in the stdout:
        /stuck-sleep $since 9 True 4 3 $last_unsued_offer $last_used_offer
        To avoid formatting issues, whitspaces are ignored.
        Explanation:
        9 Instances should be launched and $since timestamp ends with `Z`.
        """
        assert 'Z9' in decoded.replace(' ', '')


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_list_pod_json():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'list', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'overdue' in decoded
        assert '/stuck-pod' in decoded
        assert '"reason": "UnfulfilledConstraint"' in decoded


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_summary():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'summary', '/stuck-sleep'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'CONSTRAINTS' in decoded
        assert "[['hostname', 'UNIQUE']]" in decoded
        assert '0.00%' in decoded


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_summary_json():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'summary', '/stuck-sleep', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' in decoded


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_summary_pod():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'summary', '/stuck-pod'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'CONSTRAINTS' in decoded
        assert "'operator': 'unique'" in decoded
        assert "'fieldName': 'hostname'" in decoded
        assert '0.00%' in decoded


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_summary_pod_json():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'summary', '/stuck-pod', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' in decoded


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_details():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-sleep'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        """The public agent has all resources to launch this task,
        but not the matching role, therefore the output should be:
        ok        -        ok    ok   ok    ok     ok
        To avoid formatting issues, whitspaces are ignored.
        """
        assert 'ok-okokokokok' in decoded.replace(' ', '')
        """We do have 3 lines. The headline and two lines for the agents.
        If we split the decoded output by line break, there should be four
        entries in the array. The additional entry is empty.
        """
        assert len(decoded.split('\n')) == 4


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_details_json():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-sleep', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' in decoded


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_details_pod():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-pod'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        """The public agent has all resources to launch this task,
        but not the matching role, therefore the output should be:
        ok        -        ok    ok   ok    ok     ok
        To avoid formatting issues, whitspaces are ignored.
        """
        assert 'ok-okokokokok' in decoded.replace(' ', '')
        """We do have 3 lines. The headline and two lines for the agents.
        If we split the decoded output by line break, there should be four
        entries in the array. The additional entry is empty.
        """
        assert len(decoded.split('\n')) == 4


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_debug_details_pod_json():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-pod', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' in decoded


@contextlib.contextmanager
def _stuck_app(max_count=300):
    with app('tests/data/marathon/apps/stuck_sleep.json',
             'stuck-sleep', False):
        count = 0
        while count < max_count:
            tasks = _list_tasks(app_id='stuck-sleep')
            if (len(tasks) == 1):
                break
        yield


@contextlib.contextmanager
def _stuck_pod(max_count=300):
    with pod('tests/data/marathon/pods/stuck_sleep.json',
             '/stuck-pod', False):
        count = 0
        while count < max_count:
            returncode, stdout, stderr = exec_command(
                ['dcos', 'marathon', 'pod', 'list'])
            if '/stuck-pod1' in str(stdout).replace(' ', ''):
                break
        yield
