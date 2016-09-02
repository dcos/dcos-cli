from dcos import http, marathon

import mock


def test_add_pod():
    pod_json = {"some": "json"}
    rpc_client = mock.create_autospec(marathon.RpcClient)
    client = marathon.Client(rpc_client)

    client.add_pod(pod_json)

    rpc_client.http_req.assert_called_with(http.post, 'v2/pods', json=pod_json)
