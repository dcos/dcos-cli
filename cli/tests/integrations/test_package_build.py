import json
import os
import re
import tempfile
import zipfile

from shutil import rmtree

from dcos import util
from dcos.util import md5_hash_file
from dcoscli.util import formatted_cli_version
from .common import exec_command


def _success_test(build_definition,
                  expected_package_path="tests/data/build/"
                                        "package_no_references.json"):
    output_folder = tempfile.mkdtemp()

    # perform the operation
    return_code, stdout, stderr = exec_command(
        ['dcos', 'experimental', 'package', 'build', '--output-directory',
         output_folder, build_definition]
    )

    # check that the output is correct
    assert stderr == b"Created DCOS Universe package: "
    assert return_code == 0

    # check that the files created are correct
    zip_file_name = str(stdout.decode()).rstrip()

    results = re.search('^(.+)-(.+)-(.+)\.dcos', zip_file_name)

    name_result = results.group(1)
    name_expected = os.path.join(output_folder, "bitbucket")
    assert name_result == name_expected

    version_result = results.group(2)
    version_expected = "4.5"
    assert version_result == version_expected

    hash_result = results.group(3)

    print(output_folder)

    assert os.path.exists(output_folder)
    assert os.path.exists(zip_file_name), zip_file_name
    with util.open_file(zip_file_name, 'rb') as zp:
        hash_expected = md5_hash_file(zp)
    assert hash_result == hash_expected

    # check that the contents of the zip file created are correct
    with zipfile.ZipFile(zip_file_name) as zip_file:
        # package.json
        with util.open_file(expected_package_path) as pj:
            expected_metadata = util.load_json(pj)
        metadata = json.loads(zip_file.read("metadata.json").decode())
        assert metadata == expected_metadata

        # manifest.json
        expected_manifest = {'built-by': formatted_cli_version()}
        manifest = json.loads(zip_file.read("manifest.json").decode())
        assert manifest == expected_manifest

    # delete the files created
    rmtree(output_folder)


def _failure_test(build_definition, error_pattern):
    output_folder = tempfile.mkdtemp()

    # perform the operation
    return_code, stdout, stderr = exec_command(
        ['dcos', 'experimental', 'package', 'build', '--output-directory',
         output_folder, build_definition]
    )

    # check that the output is correct
    assert return_code == 1

    p = re.compile(error_pattern)
    m = p.match(stderr.decode())

    assert m, '[[' + stderr.decode() + ']]' \
              + ' did not match ' \
              + '[[' + error_pattern + ']]'
    assert stderr.decode() == m.string

    # check that no files were created in the temp folder
    assert len(os.listdir(output_folder)) == 0

    # delete the files created
    rmtree(output_folder)


def test_package_resource_only_reference():
    _success_test(
        "tests/data/build/"
        "package_resource_only_reference.json",
        expected_package_path="tests/data/build/"
                              "package_resource_only"
                              "_reference_expected.json")


def test_package_config_no_reference():
    _success_test(
        "tests/data/build/package_config_reference_expected.json",
        expected_package_path="tests/data/build/"
                              "package_config_reference_expected.json")


def test_package_config_reference():
    _success_test(
        "tests/data/build/package_config_reference.json",
        expected_package_path="tests/data/build/"
                              "package_config_reference_expected.json")


def test_package_marathon_reference():
    _success_test(
        "tests/data/build/package_marathon_reference.json",
        expected_package_path="tests/data/build/"
                              "package_marathon_reference_expected.json")


def test_package_resource_reference():
    _success_test("tests/data/build/package_resource_reference.json")


def test_package_no_references():
    _success_test("tests/data/build/package_no_references.json")


def test_package_all_references():
    _success_test("tests/data/build/package_all_references.json")


def test_package_does_not_exist():
    _failure_test("tests/data/build/does_not_exist.json",
                  "^The file \[(.+)\] does not exist.*")


def test_package_missing_references():
    _failure_test("tests/data/build/package_missing_references.json",
                  "^Error opening file "
                  "\[(.+)marathon\.json\]: "
                  "No such file or directory.*")


def test_package_reference_does_not_match_schema():
    _failure_test("tests/data/build/"
                  "package_reference_does_not_match_schema.json",
                  "^Error validating package: "
                  "\[(.+)resource-bad\.json\] "
                  "does not conform to the specified schema.*")


def test_package_no_match_schema():
    _failure_test("tests/data/build/package_no_match_schema.json",
                  "^Error validating package: "
                  "\[(.+)package_no_match_schema\.json\]"
                  " does not conform to the specified schema.*")


def test_package_badly_formed_reference():
    _failure_test("tests/data/build/package_badly_formed_reference.json",
                  "^Error validating package: "
                  "\[(.+)"
                  "package_badly_formed_reference\.json\]"
                  " does not conform to the specified schema.*")
