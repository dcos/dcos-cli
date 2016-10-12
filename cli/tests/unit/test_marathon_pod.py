import pytest
from mock import create_autospec, patch

import dcoscli.marathon.main as main
from dcos import marathon
from dcos.errors import DCOSException, DCOSHTTPException

from ..common import file_bytes
from ..fixtures.marathon import pod_list_fixture


def test_pod_add_invoked_successfully():
    _assert_pod_add_invoked_successfully(pod_file_json={"arbitrary": "json"})
    _assert_pod_add_invoked_successfully(pod_file_json=["more", "json"])


def test_pod_add_propagates_exceptions_from_add_pod():
    _assert_pod_add_propagates_exceptions_from_add_pod(DCOSException('BOOM!'))
    _assert_pod_add_propagates_exceptions_from_add_pod(Exception('Oops!'))


def test_pod_remove_invoked_successfully():
    _assert_pod_remove_invoked_successfully(pod_id='a-pod', force=False)
    _assert_pod_remove_invoked_successfully(pod_id='a-pod', force=True)
    _assert_pod_remove_invoked_successfully(pod_id='b-pod', force=False)


def test_pod_show_invoked_successfully():
    _assert_pod_show_invoked_successfully(pod_json={'id': 'a-pod', 'foo': 1})
    _assert_pod_show_invoked_successfully(pod_json={'id': 'b-pod', 'bar': 2})


def test_pod_list_with_json():
    _assert_pod_list_with_json(pod_list_json=['one', 'two', 'three'])
    _assert_pod_list_with_json(pod_list_json=[{'id': 'a'}, {'id': 'b'}])


@patch('dcoscli.marathon.main.emitter', autospec=True)
def test_pod_list_table(emitter):
    subcmd, marathon_client = _failing_reader_fixture()
    marathon_client.list_pod.return_value = pod_list_fixture()

    returncode = subcmd.pod_list(json_=False)

    assert returncode == 0
    marathon_client.list_pod.assert_called_with()
    expected_table = file_bytes('tests/unit/data/pod.txt')
    emitter.publish.assert_called_with(expected_table.decode('utf-8'))


def test_pod_update_invoked_successfully():
    _assert_pod_update_invoked_successfully(
        pod_id='foo',
        force=False,
        resource={'from': 'stdin'},
        deployment_id='a-deployment-id',
        emitted='Created deployment a-deployment-id')
    _assert_pod_update_invoked_successfully(
        pod_id='bar',
        force=False,
        resource={'from': 'stdin'},
        deployment_id='a-deployment-id',
        emitted='Created deployment a-deployment-id')
    _assert_pod_update_invoked_successfully(
        pod_id='foo',
        force=True,
        resource={'from': 'stdin'},
        deployment_id='some-arbitrary-value',
        emitted='Created deployment some-arbitrary-value')


def test_pod_update_propagates_exceptions_from_show_pod():
    resource_reader = create_autospec(main.ResourceReader)
    marathon_client = _marathon_client_fixture()
    marathon_client.show_pod.side_effect = DCOSException('show error')
    marathon_client.update_pod.side_effect = DCOSException('update error')

    _assert_pod_update_propagates_exception(
        resource_reader, marathon_client, 'show error')


def test_pod_update_propagates_dcos_exception_from_resource_reader():
    resource_reader = create_autospec(main.ResourceReader)
    resource_reader.get_resource.side_effect = DCOSException('IO error')
    marathon_client = _marathon_client_fixture()

    _assert_pod_update_propagates_exception(
        resource_reader, marathon_client, 'IO error')


def test_pod_update_propagates_dcos_exception_from_update_pod():
    resource_reader = create_autospec(main.ResourceReader)
    marathon_client = _marathon_client_fixture()
    marathon_client.update_pod.side_effect = DCOSException('update error')

    _assert_pod_update_propagates_exception(
        resource_reader, marathon_client, 'update error')


def test_pod_kill_invoked_successfully():
    pod_id = 'foo'
    instance_ids = ['instance1', 'instance2']
    subcmd, marathon_client = _failing_reader_fixture()

    returncode = subcmd.pod_kill(pod_id, instance_ids)

    assert returncode == 0
    marathon_client.kill_pod_instances.assert_called_with(pod_id, instance_ids)


def test_pod_kill_reports_error_when_no_instance_ids_are_provided():
    def no_marathon_client():
        assert False, "should not be called"

    subcmd = main.MarathonSubcommand(_failing_resource_reader(),
                                     no_marathon_client)

    with pytest.raises(DCOSException) as exception_info:
        subcmd.pod_kill('arbitrary', [])

    message = 'Please provide at least one pod instance ID'
    assert str(exception_info.value) == message


def test_pod_command_fails_if_not_supported():
    def test_case(invoke_command):
        subcmd, marathon_client = _failing_reader_fixture()
        marathon_client.pod_feature_supported.return_value = False

        with pytest.raises(DCOSException) as exception_info:
            invoke_command(subcmd)

        message = 'This command is not supported by your version of Marathon'
        assert str(exception_info.value) == message

    test_case(_default_pod_add)
    test_case(_default_pod_remove)
    test_case(_default_pod_list)
    test_case(_default_pod_show)
    test_case(_default_pod_update)
    test_case(_default_pod_kill)


def test_pod_command_propagates_exceptions_from_support_check():
    def test_case(invoke_command, exception):
        subcmd, marathon_client = _failing_reader_fixture()
        marathon_client.pod_feature_supported.side_effect = exception

        with pytest.raises(exception.__class__) as exception_info:
            invoke_command(subcmd)

        assert exception_info.value == exception

    test_case(_default_pod_add, DCOSException('BOOM!'))
    test_case(_default_pod_remove, DCOSHTTPException(None))
    test_case(_default_pod_list, ValueError('Oops'))
    test_case(_default_pod_show, IOError('Bad stuff'))
    test_case(_default_pod_update, Exception('uh oh'))
    test_case(_default_pod_kill, Exception('problem'))


def test_pod_command_propagates_exceptions_from_marathon_client():
    def test_single_exception(invoke_command, marathon_method, exception):
        subcmd, marathon_client = _failing_reader_fixture()
        marathon_method(marathon_client).side_effect = exception

        with pytest.raises(exception.__class__) as exception_info:
            invoke_command(subcmd)

        assert exception_info.value == exception

    def test_several_exceptions(invoke_command, marathon_method):
        test_single_exception(
            invoke_command, marathon_method, DCOSException('BOOM!'))
        test_single_exception(
            invoke_command, marathon_method, Exception('Oops!'))

    test_several_exceptions(
        _default_pod_remove,
        lambda marathon_client: marathon_client.remove_pod)
    test_several_exceptions(
        _default_pod_show,
        lambda marathon_client: marathon_client.show_pod)
    test_several_exceptions(
        _default_pod_list,
        lambda marathon_client: marathon_client.list_pod)
    test_several_exceptions(
        _default_pod_kill,
        lambda marathon_client: marathon_client.kill_pod_instances)


def _assert_pod_add_invoked_successfully(pod_file_json):
    pod_file_path = "some/path/to/pod.json"
    resource_reader = create_autospec(main.ResourceReader)
    resource_reader.get_resource.return_value = pod_file_json
    marathon_client = _marathon_client_fixture()

    subcmd = main.MarathonSubcommand(resource_reader, lambda: marathon_client)
    returncode = subcmd.pod_add(pod_file_path)

    assert returncode == 0
    resource_reader.get_resource.assert_called_with(pod_file_path)
    marathon_client.add_pod.assert_called_with(pod_file_json)


def _assert_pod_add_propagates_exceptions_from_add_pod(exception):
    resource_reader = create_autospec(main.ResourceReader)
    resource_reader.get_resource.return_value = {'some': 'json'}

    marathon_client = _marathon_client_fixture()
    marathon_client.add_pod.side_effect = exception

    subcmd = main.MarathonSubcommand(resource_reader, lambda: marathon_client)
    with pytest.raises(exception.__class__) as exception_info:
        subcmd.pod_add('does/not/matter')

    assert exception_info.value == exception


def _assert_pod_remove_invoked_successfully(pod_id, force):
    subcmd, marathon_client = _failing_reader_fixture()

    returncode = subcmd.pod_remove(pod_id, force)

    assert returncode == 0
    marathon_client.remove_pod.assert_called_with(pod_id, force)


@patch('dcoscli.marathon.main.emitter', autospec=True)
def _assert_pod_show_invoked_successfully(emitter, pod_json):
    subcmd, marathon_client = _failing_reader_fixture()
    marathon_client.show_pod.return_value = pod_json

    returncode = subcmd.pod_show(pod_json['id'])

    assert returncode == 0
    marathon_client.show_pod.assert_called_with(pod_json['id'])
    emitter.publish.assert_called_with(pod_json)


@patch('dcoscli.marathon.main.emitter', autospec=True)
def _assert_pod_list_with_json(emitter, pod_list_json):
    subcmd, marathon_client = _failing_reader_fixture()
    marathon_client.list_pod.return_value = pod_list_json

    subcmd.pod_list(json_=True)

    emitter.publish.assert_called_with(pod_list_json)


@patch('dcoscli.marathon.main.emitter', autospec=True)
def _assert_pod_update_invoked_successfully(
        emitter, pod_id, force, resource, deployment_id, emitted):
    resource_reader = create_autospec(main.ResourceReader)
    resource_reader.get_resource.return_value = resource

    marathon_client = _marathon_client_fixture()
    marathon_client.update_pod.return_value = deployment_id

    subcmd = main.MarathonSubcommand(resource_reader, lambda: marathon_client)
    returncode = subcmd.pod_update(pod_id, force)

    assert returncode == 0
    marathon_client.show_pod.assert_called_with(pod_id)
    resource_reader.get_resource.assert_called_with(name=None)
    marathon_client.update_pod.assert_called_with(
        pod_id, pod_json=resource, force=force)
    emitter.publish.assert_called_with(emitted)


def _assert_pod_update_propagates_exception(
        resource_reader, marathon_client, error_message):
    subcmd = main.MarathonSubcommand(resource_reader, lambda: marathon_client)

    with pytest.raises(DCOSException) as exception_info:
        subcmd.pod_update(pod_id='foo', force=False)

    assert str(exception_info.value) == error_message


def _marathon_client_fixture():
    marathon_client = create_autospec(marathon.Client)
    marathon_client.pod_feature_supported.return_value = True
    return marathon_client


def _failing_reader_fixture():
    marathon_client = _marathon_client_fixture()
    subcmd = main.MarathonSubcommand(_failing_resource_reader(),
                                     lambda: marathon_client)

    return subcmd, marathon_client


def _failing_resource_reader():
    resource_reader = create_autospec(main.ResourceReader)
    error = AssertionError("should not be called")
    resource_reader.get_resource.side_effect = error
    resource_reader.get_resource_from_properties.side_effect = error
    return resource_reader


def _default_pod_add(subcmd):
    return subcmd.pod_add(pod_resource_path='not/used')


def _default_pod_remove(subcmd):
    return subcmd.pod_remove(pod_id='some-id', force=False)


def _default_pod_list(subcmd):
    return subcmd.pod_list(json_=False)


def _default_pod_show(subcmd):
    return subcmd.pod_show(pod_id='some-id')


def _default_pod_update(subcmd):
    return subcmd.pod_update(pod_id='some-id', force=False)


def _default_pod_kill(subcmd):
    return subcmd.pod_kill(pod_id='some-id', instance_ids=['some-instance'])
