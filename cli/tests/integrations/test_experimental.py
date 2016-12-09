import contextlib
import json
import os
import re
import shutil
import tempfile
import zipfile

import pytest

from dcos import util
from dcoscli.util import formatted_cli_version
from .common import assert_command, exec_command, watch_all_deployments

command_base = ['dcos', 'experimental']
experimental_data_dir = os.path.join(
    os.getcwd(), 'tests', 'data', 'experimental')
build_data_dir = os.path.join(
    experimental_data_dir, 'package_build')
cassandra_path = os.path.join(
    experimental_data_dir, 'cassandra', 'package.json')


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
        package_build_failure(build_definition_path,
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
        package_build_failure(build_definition_path,
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
        package_build_failure(build_definition_path,
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
        package_build_failure(bad_build_definition_path,
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
        package_build_failure(bad_build_definition_path,
                              output_directory,
                              stderr=stderr)


# TODO: Add cleanup to tests
@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_package_add_argument_exclussion():
    command = command_base + ['package', 'add',
                              '--dcos-package', cassandra_path,
                              '--package-version', '3.0']
    code, out, err = exec_command(command)
    assert code == 1
    assert err == b''

    stdout = out.decode()
    not_recognized = 'Command not recognized'
    add_command = """\
    dcos experimental package add (--dcos-package=<dcos-package> |
                                    (--package-name=<package-name>
                                    """
    """[--package-version=<package-version>]))"""
    assert not_recognized in stdout
    assert add_command in stdout


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_happy_path():
    with _temporary_directory() as output_directory:
        cassandra_package = package_build(cassandra_path, output_directory)
        name, version = package_add(cassandra_package)
        service_start(name, version)
        service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_happy_path_from_universe():
    package_name = 'linkerd'
    name, version = package_add_universe(package_name)
    service_start(name, version)
    service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_by_starting_same_service_twice():
    # Assumes that cassandra has been added in the past
    name = 'cassandra'
    version = '1.0.20-3.0.10'
    service_start(name, version)
    stderr = b'Package is already installed\n'
    service_start_failure(name, version, stderr=stderr)
    service_stop(name)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-11989")
def test_service_start_by_starting_service_not_added():
    stderr = b'Package [foo] not found\n'
    service_start_failure('foo', stderr=stderr)


def service_stop(package_name):
    command = ['dcos', 'package', 'uninstall', package_name]
    code, out, err = exec_command(command)
    watch_all_deployments()
    assert code == 0
    return err == b''


def service_list():
    command = ['dcos', 'package', 'list', '--json']
    code, out, err = exec_command(command)
    assert code == 0
    assert err == b''
    return json.loads(out.decode())


def service_start(package_name, package_version=None, options=None):
    command = command_base + ['service', 'start', package_name]
    if package_version is not None:
        command += ['--package-version', package_version]
    if options is not None:
        command += ['--options', options]

    code, out, err = exec_command(command)
    assert code == 0
    assert err == b''
    assert out == b''

    running_services = service_list()
    assert package_name in map(lambda pkg: pkg['name'], running_services)


def service_start_failure(package_name,
                          package_version=None,
                          options=None,
                          return_code=1,
                          stdout=b'',
                          stderr=b''):
    command = command_base + ['service', 'start', package_name]
    if package_version is not None:
        command += ['--package-version', package_version]
    if options is not None:
        command += ['--options', options]

    assert_command(command,
                   returncode=return_code,
                   stdout=stdout,
                   stderr=stderr)


def package_add(package):
    command = command_base + ['package', 'add', '--dcos-package', package]

    code, out, err = exec_command(command)
    assert code == 0
    assert err == b''

    metadata = json.loads(out.decode())
    metadata.pop('releaseVersion')
    assert metadata == _get_json_in_zip(package, 'metadata.json')

    return metadata['name'], metadata['version']


def package_add_universe(package_name, package_version=None):
    command = command_base + ['package', 'add',
                              '--package-name', package_name]
    if package_version is not None:
        command += ['--package-version', package_version]

    code, out, err = exec_command(command)

    assert code == 0
    assert err == b''

    metadata = json.loads(out.decode())
    return metadata['name'], metadata['version']


def package_build(build_definition_path,
                  output_directory,
                  metadata=None,
                  manifest=None):
    command = command_base + ['package', 'build',
                              '--output-directory', output_directory,
                              build_definition_path]

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


def _get_default_manifest():
    return {'built-by': formatted_cli_version()}


def package_build_failure(build_definition_path,
                          output_directory,
                          return_code=1,
                          stdout=b'',
                          stderr=b''):
    command = command_base + ['package', 'build',
                              '--output-directory', output_directory,
                              build_definition_path]
    assert_command(command,
                   returncode=return_code,
                   stdout=stdout,
                   stderr=stderr)
    assert len(os.listdir(output_directory)) == 0


def _successful_package_build_test(
        build_definition_path,
        expected_package_path=os.path.join(
            build_data_dir,
            "package_no_references.json"
        )):
    with _temporary_directory() as output_directory:
        metadata = _get_json(expected_package_path)
        manifest = _get_default_manifest()
        package_build(build_definition_path,
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
