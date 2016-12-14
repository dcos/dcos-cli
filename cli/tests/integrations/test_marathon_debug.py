import contextlib
import json
import re

from .common import (app, exec_command, pod)
from .test_marathon import (_list_tasks)

list_regex = '/stuck-(?:sleep|pod)\W+[^Z]+Z\W+9\W+(?:True|False)' \
             '\W+\d\W+\d\W+[^Z]+Z\W+[^Z]+Z'


def test_debug_list():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'list'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'WAITING' in decoded
        assert '/stuck-sleep' in decoded
        """A line in the output looks like
        /stuck-sleep $since 9 True 4 3 $last_unsued_offer $last_used_offer
        Therefore `list_regex` tests this
        """
        assert re.search(list_regex, decoded) is not None


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


def test_debug_list_pod():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'list'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'WAITING' in decoded
        assert '/stuck-pod' in decoded
        """A line in the output looks like
        /stuck-sleep $since 9 True 4 3 $last_unsued_offer $last_used_offer
        Therefore `list_regex` tests this
        """
        assert re.search(list_regex, decoded) is not None


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


def test_debug_summary_json():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'summary', '/stuck-sleep', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' \
               in decoded


def test_debug_summary_pod():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'summary', '/stuck-pod'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        assert 'CONSTRAINTS' in decoded
        assert "'operator': 'UNIQUE'" in decoded
        assert "'fieldName': 'hostname'" in decoded
        assert '0.00%' in decoded


def test_debug_summary_pod_json():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'summary', '/stuck-pod', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' \
               in decoded


def test_debug_details():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-sleep'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        """The public agent has all resources to launch this task,
        but not the matching role, therefore the output should be:
        ok        -        ok    ok   ok    ok
        To avoid formatting issues, whitespaces are ignored.
        """
        assert 'ok-okokokok' in decoded.replace(' ', '')

        returncode, stdout, stderr = exec_command(['dcos', 'node', '--json'])

        assert returncode == 0
        assert stderr == b''
        agent_count = len(json.loads(stdout.decode('utf-8')))

        """The extra two lines come from the heading and the empty line at the
        end of the table.
        """
        assert len(decoded.split('\n')) == agent_count + 2


def test_debug_details_json():
    with _stuck_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-sleep', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' \
               in decoded


def test_debug_details_pod():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-pod'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode()
        """The public agent has all resources to launch this task,
        but not the matching role, therefore the output should be:
        ok        -        ok    ok   ok    ok
        To avoid formatting issues, whitespaces are ignored.
        """
        assert 'ok-okokokok' in decoded.replace(' ', '')

        returncode, stdout, stderr = exec_command(['dcos', 'node', '--json'])

        assert returncode == 0
        assert stderr == b''
        agent_count = len(json.loads(stdout.decode('utf-8')))

        """The extra two lines come from the heading and the empty line at the
        end of the table.
        """
        assert len(decoded.split('\n')) == agent_count + 2


def test_debug_details_pod_json():
    with _stuck_pod():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'debug', 'details', '/stuck-pod', '--json'])

        assert returncode == 0
        assert stderr == b''

        decoded = stdout.decode().replace(' ', '').replace('\n', '')
        assert '"reason":"UnfulfilledConstraint"' in decoded
        assert '{"declined":0,"processed":0,"reason":"InsufficientCpus"}' \
               in decoded


@contextlib.contextmanager
def _stuck_app(max_count=300):
    with app('tests/data/marathon/apps/stuck_sleep.json',
             'stuck-sleep', False):
        count = 0
        while count < max_count:
            tasks = _list_tasks(app_id='stuck-sleep')
            if len(tasks) == 1:
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
