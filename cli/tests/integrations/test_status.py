import json
import re

import six

from .common import exec_command

TEST_CLUSTER_STATUS = {'master': 'alive', 'marathon': 'busy'}


def test_help():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'status', '--help'])

    assert returncode == 0
    assert stdout == b"""Get the status of the DCOS cluster

Usage:
   dcos status --info
   dcos status --version
   dcos status [--json]

Options:
    --help                  Show this screen
    --info                  Show info
    --json                  Print json-formatted cluster status
    --version               Show version
"""
    assert stderr == b''


def test_status():
    returncode, stdout, stderr = exec_command(['dcos', 'status'])
    decoded_stdout = stdout.decode('utf-8')
    assert returncode == 0
    assert "DCOS UI                    OK" in decoded_stdout
    assert "Exhibitor                  OK" in decoded_stdout
    assert "Marathon                   OK" in decoded_stdout
    assert "Mesos Marathon framework   OK" in decoded_stdout
    assert "Mesos Master               OK" in decoded_stdout
    assert "Mesos active Slaves count" in decoded_stdout
    assert int(re.search(r'\d+', decoded_stdout).group()) > 0
    assert stderr == b''


def test_status_json():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'status', '--json'])
    assert returncode == 0
    result = json.loads(stdout.decode('utf-8'))

    assert six.next(item for item in result if
                    item["Name"] == "Mesos Master")["Status"] == "OK"
    assert six.next(item for item in result if
                    item["Name"] == "Mesos Marathon"
                                    " framework")["Status"] == "OK"
    assert six.next(item for item in result if
                    item["Name"] == "Mesos active"
                                    " Slaves count")["Status"] > 0
    assert six.next(item for item in result if
                    item["Name"] == "Marathon")["Status"] == "OK"
    assert six.next(item for item in result if
                    item["Name"] == "DCOS UI")["Status"] == "OK"
    assert six.next(item for item in result if
                    item["Name"] == "Exhibitor")["Status"] == "OK"
