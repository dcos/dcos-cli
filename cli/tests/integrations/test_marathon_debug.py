import contextlib
import json
import re
import retrying

from .helpers.common import exec_command
from .helpers.marathon import app, pod, watch_for_overdue

list_regex = '/stuck-(?:sleep|pod)\W+[^Z]+Z\W+\d\W+(?:True|False)' \
             '\W+\d{1,2}\W+\d{1,2}\W+[^Z]+Z\W+[^Z]+Z'


def test_debug_list():
    with _stuck_app():
        check_debug_list()


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


@retrying.retry(wait_fixed=1000, stop_max_attempt_number=30)
def check_debug_list():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'debug', 'list'])

    assert returncode == 0
    assert stderr == b''

    decoded = stdout.decode()
    assert 'WAITING' in decoded
    """A line in the output looks like
    /stuck-sleep $since 9 True 4 3 $last_unsued_offer $last_used_offer
    Therefore `list_regex` tests this
    """
    assert re.search(list_regex, decoded) is not None


def test_debug_list_pod():
    with _stuck_pod():
        check_debug_list()


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
        @retrying.retry(wait_fixed=1000, stop_max_attempt_number=30)
        def check_debug_summary():
            returncode, stdout, stderr = exec_command(
                ['dcos', 'marathon', 'debug', 'summary', '/stuck-sleep'])

            assert returncode == 0
            assert stderr == b''

            decoded = stdout.decode()
            assert 'CONSTRAINTS' in decoded
            assert "[['hostname', 'UNIQUE']]" in decoded
            assert '0.00%' in decoded
        check_debug_summary()


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
        @retrying.retry(wait_fixed=1000, stop_max_attempt_number=30)
        def check_debug_summary():
            returncode, stdout, stderr = exec_command(
                ['dcos', 'marathon', 'debug', 'summary', '/stuck-pod'])

            assert returncode == 0
            assert stderr == b''

            decoded = stdout.decode()
            assert 'CONSTRAINTS' in decoded
            assert "'operator': 'UNIQUE'" in decoded
            assert "'fieldName': 'hostname'" in decoded
            assert '0.00%' in decoded

        check_debug_summary()


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
        check_debug_details('/stuck-sleep')


@retrying.retry(wait_fixed=1000, stop_max_attempt_number=30)
def check_debug_details(id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'debug', 'details', id])

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
    agent_count = len(
      [n for n in json.loads(stdout.decode('utf-8'))
       if n['type'] == 'agent']
    )

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
        check_debug_details('/stuck-pod')


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
        watch_for_overdue(max_count)
        yield


@contextlib.contextmanager
def _stuck_pod(max_count=300):
    with pod('tests/data/marathon/pods/stuck_sleep.json',
             '/stuck-pod', False):
        watch_for_overdue(max_count)
        yield
