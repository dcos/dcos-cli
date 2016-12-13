import contextlib
import json
import os
import re
import shutil
import tempfile
import time
import zipfile

import pytest

from dcos import util
from dcoscli.util import formatted_cli_version
from .common import assert_command, exec_command, watch_all_deployments

command_base = ['dcos', 'experimental']
data_dir = os.path.join(
    os.getcwd(), 'tests', 'data'
)
build_data_dir = os.path.join(
    data_dir, 'package_build'
)
runnable_package_path = os.path.join(
    build_data_dir, 'helloworld', 'package.json'
)


def test_experimental():
    command = command_base + ['--help']
    with open('dcoscli/data/help/experimental.txt') as content:
        assert_command(command, stdout=content.read().encode())


def test_info():
    command = command_base + ['--info']
    out = b'Experimental commands. These commands ' \
          b'are under development and are subject to change\n'
    assert_command(command, stdout=out)


def test_version():
    command = command_base + ['--version']
    out = b'dcos-experimental version SNAPSHOT\n'
    assert_command(command, stdout=out)


def test_package_build_with_only_resources_with_only_resources_reference():
    _successful_package_build_test(
        os.path.join(
            build_data_dir,
            "package_resource_only_reference.json"),
        expected_package_path=os.path.join(
            build_data_dir,
            "package_resource_only_reference_expected.json"))


def test_package_build_with_only_config_with_no_references():
    _successful_package_build_test(
        os.path.join(
            build_data_dir,
            "package_config_reference_expected.json"),
        expected_package_path=os.path.join(
            build_data_dir,
            "package_config_reference_expected.json"))


def test_package_build_with_only_config_with_only_config_reference():
    _successful_package_build_test(
        os.path.join(
            build_data_dir,
            "package_config_reference.json"),
        expected_package_path=os.path.join(
            build_data_dir,
            "package_config_reference_expected.json"))


def test_package_build_with_only_marathon_with_only_marathon_reference():
    _successful_package_build_test(
        os.path.join(
            build_data_dir,
            "package_marathon_reference.json"),
        expected_package_path=os.path.join(
            build_data_dir,
            "package_marathon_reference_expected.json"))


def test_package_build_with_only_resource_reference():
    _successful_package_build_test(
        os.path.join(
            build_data_dir,
            "package_resource_reference.json"))


def test_package_build_with_no_references():
    _successful_package_build_test(
        os.path.join(
            build_data_dir,
            "package_no_references.json"))


def test_package_build_with_all_references():
    _successful_package_build_test(
        os.path.join(
            build_data_dir,
            "package_all_references.json"))


def test_package_build_where_build_definition_does_not_exist():
    with _temporary_directory() as output_directory:
        build_definition_path = os.path.join(build_data_dir,
                                             "does_not_exist.json")
        stderr = ("The file [{}] does not exist\n"
                  .format(build_definition_path)
                  .encode())
        _package_build_failure(build_definition_path,
                               output_directory,
                               stderr=stderr)


def test_package_build_where_project_is_missing_references():
    with _temporary_directory() as output_directory:
        build_definition_path = (
            os.path.join(build_data_dir,
                         "package_missing_references.json"))
        marathon_json_path = os.path.join(build_data_dir,
                                          "marathon.json")
        stderr = ("Error opening file [{}]: No such file or directory\n"
                  .format(marathon_json_path)
                  .encode())
        _package_build_failure(build_definition_path,
                               output_directory,
                               stderr=stderr)


def test_package_build_where_reference_does_not_match_schema():
    with _temporary_directory() as output_directory:
        build_definition_path = os.path.join(
            build_data_dir,
            "package_reference_does_not_match_schema.json"
        )
        bad_resource_path = os.path.join(
            build_data_dir,
            "resource-bad.json"
        )
        stderr = ("Error validating package: "
                  "[{}] does not conform to the specified schema\n"
                  .format(bad_resource_path)
                  .encode())
        _package_build_failure(build_definition_path,
                               output_directory,
                               stderr=stderr)


def test_package_build_where_build_definition_does_not_match_schema():
    with _temporary_directory() as output_directory:
        bad_build_definition_path = os.path.join(
            build_data_dir,
            "package_no_match_schema.json"
        )
        stderr = ("Error validating package: "
                  "[{}] does not conform to the specified schema\n"
                  .format(bad_build_definition_path)
                  .encode())
        _package_build_failure(bad_build_definition_path,
                               output_directory,
                               stderr=stderr)


def test_package_build_where_build_definition_has_badly_formed_reference():
    with _temporary_directory() as output_directory:
        bad_build_definition_path = os.path.join(
            build_data_dir,
            "package_badly_formed_reference.json"
        )
        stderr = ("Error validating package: "
                  "[{}] does not conform to the specified schema\n"
                  .format(bad_build_definition_path)
                  .encode())
        _package_build_failure(bad_build_definition_path,
                               output_directory,
                               stderr=stderr)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_package_add_argument_exclussion():
    command = command_base + ['package', 'add',
                              '--dcos-package', runnable_package_path,
                              '--package-version', '3.0']
    code, out, err = exec_command(command)
    assert code == 1
    assert err == b''

    stdout = out.decode()
    not_recognized = 'Command not recognized'
    assert not_recognized in stdout


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_happy_path():
    with _temporary_directory() as output_directory:
        runnable_package = _package_build(
            runnable_package_path, output_directory)
        name, version = _package_add(runnable_package)
        _wait_for_package_add_local(runnable_package)
        try:
            _service_start(name, version)
        finally:
            _service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_happy_path_json():
    with _temporary_directory() as output_directory:
        runnable_package = _package_build(
            runnable_package_path, output_directory)
        name, version = _package_add(runnable_package, expects_json=True)
        _wait_for_package_add_local(runnable_package)
        try:
            _service_start(name, version, expects_json=True)
        finally:
            _service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_happy_path_from_universe():
    package_name = 'linkerd'
    name, version = _package_add_universe(package_name)
    _wait_for_package_add_remote(name, version)
    try:
        _service_start(name, version)
    finally:
        _service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_happy_path_from_universe_json():
    package_name = 'linkerd'
    name, version = _package_add_universe(package_name, expects_json=True)
    _wait_for_package_add_remote(name, version)
    try:
        _service_start(name, version)
    finally:
        _service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_by_starting_same_service_twice():
    name, version = _package_add_universe('linkerd')
    try:
        _service_start(name, version)
        stderr = b'Package is already installed\n'
        _service_start_failure(name, version, stderr=stderr)
    finally:
        _service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_by_starting_service_not_added():
    stderr = b'Package [foo] not found\n'
    _service_start_failure('foo', stderr=stderr)


def _service_stop_cmd(package_name):
    return ['dcos', 'package', 'uninstall', package_name]


def _service_list_cmd():
    return ['dcos', 'package', 'list', '--json']


def _service_start_cmd(package_name,
                       package_version=None,
                       options=None,
                       json=False):
    return (command_base
            + (['service', 'start'])
            + (['--json'] if json else [])
            + ([package_name])
            + (['--package-version', package_version]
               if package_version else [])
            + (['--options', options] if options else []))


def _package_add_cmd(dcos_package=None,
                     package_name=None,
                     package_version=None,
                     json=False):
    return (command_base
            + (['package', 'add'])
            + (['--json'] if json else [])
            + (['--dcos-package', dcos_package] if dcos_package else [])
            + (['--package-name', package_name] if package_name else [])
            + (['--package-version', package_version]
               if package_version else []))


def _package_build_cmd(build_definition, output_directory=None):
    return (command_base
            + (['package', 'build'])
            + (['--output-directory', output_directory]
               if output_directory else [])
            + ([build_definition]))


def _service_stop(package_name):
    command = _service_stop_cmd(package_name)
    exec_command(command)
    watch_all_deployments()


def _service_list():
    command = _service_list_cmd()
    code, out, err = exec_command(command)
    assert code == 0
    assert err == b''
    return json.loads(out.decode())


def _service_start(package_name,
                   package_version,
                   options=None,
                   expects_json=False):
    command = _service_start_cmd(package_name,
                                 package_version,
                                 options,
                                 json=expects_json)
    code, out, err = exec_command(command)
    assert code == 0
    assert err == b''

    if expects_json:
        expected = {
            'packageName': package_name,
            'packageVersion': package_version
        }
        actual = json.loads(out.decode())
        actual.pop('appId')
        assert expected == actual, (expected, actual)
    else:
        stdout = 'The service [{}] version [{}] has been started\n'.format(
            package_name, package_version).encode()
        assert out == stdout, (out, stdout)

    running_services = _service_list()
    assert package_name in map(lambda pkg: pkg['name'], running_services)


def _service_start_failure(package_name,
                           package_version=None,
                           options=None,
                           return_code=1,
                           stdout=b'',
                           stderr=b''):
    command = _service_start_cmd(package_name,
                                 package_version,
                                 options)
    assert_command(command,
                   returncode=return_code,
                   stdout=stdout,
                   stderr=stderr)


def _package_add(package, expects_json=False):
    command = _package_add_cmd(dcos_package=package, json=expects_json)
    code, out, err = exec_command(command)
    assert code == 0
    assert err == b''
    if expects_json:
        metadata = json.loads(out.decode())
        metadata.pop('releaseVersion')
        assert metadata == _get_json_in_zip(package, 'metadata.json')
    else:
        metadata = _get_json_in_zip(package, 'metadata.json')
        stdout = (
            'The package [{}] version [{}] has been added to DC/OS\n'.format(
                metadata['name'], metadata['version'])).encode()
        assert out == stdout, (out, stdout)

    return metadata['name'], metadata['version']


def _package_add_universe(package_name,
                          package_version=None,
                          expects_json=False):
    command = _package_add_cmd(package_name=package_name,
                               package_version=package_version,
                               json=expects_json)
    code, out, err = exec_command(command)
    assert code == 0
    assert err == b''
    if expects_json:
        metadata = json.loads(out.decode())
        name = metadata['name']
        version = metadata['version']
    else:
        name_version = re.search("\[(.*)\].*\[(.*)\]", out.decode())
        name = name_version.group(1)
        version = name_version.group(2)
        stdout = (
            'The package [{}] version [{}] has been added to DC/OS\n'.format(
                name, version)).encode()
        assert out == stdout, (out, stdout)

    assert name == package_name
    assert version == package_version if package_version else True

    return name, version


def _package_build(build_definition_path,
                   output_directory,
                   metadata=None,
                   manifest=None):
    command = _package_build_cmd(build_definition_path,
                                 output_directory)

    code, out, err = exec_command(command)
    assert code == 0
    assert err == b'Created DCOS Universe package: '

    package_path = out.decode().rstrip()
    assert os.path.exists(package_path)

    name, version, md5 = _decompose_name(package_path)
    build_definition = _get_json(build_definition_path)
    assert name == build_definition['name']
    assert version == build_definition['version']
    assert md5 == _get_md5_hash(package_path)
    assert (manifest is None or
            manifest == _get_json_in_zip(package_path, 'manifest.json'))
    assert (metadata is None or
            metadata == _get_json_in_zip(package_path, 'metadata.json'))

    return package_path


def _package_build_failure(build_definition_path,
                           output_directory,
                           return_code=1,
                           stdout=b'',
                           stderr=b''):
    command = _package_build_cmd(build_definition_path, output_directory)

    assert_command(command,
                   returncode=return_code,
                   stdout=stdout,
                   stderr=stderr)
    assert len(os.listdir(output_directory)) == 0


def _wait_for_package_add_remote(package_name, package_version):
    command = _package_add_cmd(package_name=package_name,
                               package_version=package_version)
    _wait_for_package_add(command, package_name, package_version)


def _wait_for_package_add_local(package):
    command = _package_add_cmd(dcos_package=package)
    metadata = _get_json_in_zip(package, 'metadata.json')
    name = metadata['name']
    version = metadata['version']
    _wait_for_package_add(command, name, version)


def _wait_for_package_add(command, name, version):
    done_adding = False
    max_retries = 10
    retry_number = 0
    while not done_adding:
        code, out, err = exec_command(command)
        change_in_progress_message = (
            'A change to package '
            '{}-{} is already in progress\n'.format(
                name, version).encode())
        done_adding = code == 0
        assert (done_adding or
                (code == 1 and
                 err == change_in_progress_message))
        assert retry_number != max_retries, \
            'Waiting for package add to complete took too long'
        retry_number += 1
        time.sleep(5)


def _get_default_manifest():
    return {'built-by': formatted_cli_version()}


def _successful_package_build_test(
        build_definition_path,
        expected_package_path=os.path.join(
            build_data_dir,
            "package_no_references.json"
        )):
    with _temporary_directory() as output_directory:
        metadata = _get_json(expected_package_path)
        manifest = _get_default_manifest()
        _package_build(build_definition_path,
                       output_directory,
                       metadata=metadata,
                       manifest=manifest)


def _decompose_name(package_path):
    parts = re.search(
        '^([^-]+)-(.+)-([^-]+)\.dcos',
        os.path.basename(package_path))
    assert parts is not None, package_path
    return parts.group(1), parts.group(2), parts.group(3)


def _get_md5_hash(path):
    with open(path, 'rb') as f:
        return util.md5_hash_file(f)


def _get_json(path):
    with open(path) as f:
        file_contents = f.read()
    return json.loads(file_contents)


def _get_json_in_zip(path, inner_file):
    with zipfile.ZipFile(path) as zip_file:
        inner_file_contents = zip_file.read(inner_file).decode()
    return json.loads(inner_file_contents)


@contextlib.contextmanager
def _temporary_directory():
    tmp_dir = tempfile.mkdtemp()
    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir)
