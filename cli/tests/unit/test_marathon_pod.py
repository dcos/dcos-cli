import dcoscli.marathon.main as main
from dcos import marathon

from mock import create_autospec


def test_add_invoked_successfully():
    _assert_add_invoked_successfully(pod_file_json={"arbitrary": "json"})
    _assert_add_invoked_successfully(pod_file_json=["more", "json"])


def _assert_add_invoked_successfully(pod_file_json):
    pod_file_path = "some/path/to/pod.json"
    resource_reader = {pod_file_path: pod_file_json}.__getitem__
    marathon_client = create_autospec(marathon.Client)

    pod = main.MarathonPodSubcommand(resource_reader, marathon_client)
    returncode = pod.add(pod_file_path)

    assert returncode == 0
    marathon_client.add_pod.assert_called_with(pod_file_json)
