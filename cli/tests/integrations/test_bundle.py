import json
import os
import re
import tempfile
import zipfile

from shutil import rmtree

from dcos import util
from dcos.util import hash_file
from .common import exec_command


def _success_test(package_json):
    output_folder = tempfile.mkdtemp()
    expected_path = "tests/data/bundle/package_no_references.json"

    # perform the operation
    return_code, stdout, stderr = exec_command(
        ['dcos', 'package', 'bundle', '--output-directory',
         output_folder, package_json]
    )

    # check that the output is correct
    pattern = re.compile("^Created DCOS Universe package")
    assert return_code == 0
    assert pattern.match(stdout.decode())
    assert stderr == b""

    # check that the files created are correct
    zip_file_name = re.search('^Created DCOS Universe package \[(.+?)\].', stdout.decode()).group(1)
    results = re.search('^(.+)-(.+)-(.+)\.dcos', zip_file_name)

    name_result = results.group(1)
    name_expected = os.path.join(output_folder, "bitbucket")
    assert name_result == name_expected

    version_result = results.group(2)
    version_expected = "4.5"
    assert version_result == version_expected

    hash_result = results.group(3)
    hash_expected = hash_file(zip_file_name)
    assert hash_result == hash_expected

    # check that the contents of the zip file created are correct
    with zipfile.ZipFile(zip_file_name) as zip_file:
        with util.open_file(expected_path) as pj:
            expected = util.load_json(pj)
        actual = json.loads(zip_file.read("package.json").decode())
        assert actual == expected

    # delete the files created
    rmtree(output_folder)


def _failure_test(package_json, error_pattern):
    output_folder = tempfile.mkdtemp()

    # perform the operation
    return_code, stdout, stderr = exec_command(
        ['dcos', 'package', 'bundle', '--output-directory',
         output_folder, package_json]
    )

    # check that the output is correct
    assert return_code == 1

    p = re.compile(error_pattern)
    assert p.match(stderr.decode())

    # check that no files were created in the temp folder
    assert len(os.listdir(output_folder)) == 0

    # delete the files created
    rmtree(output_folder)


def test_package_no_references():
    _success_test("tests/data/bundle/package_no_references.json")


def test_package_all_references():
    _success_test("tests/data/bundle/package_all_references.json")


def test_package_missing_references():
    _failure_test("tests/data/bundle/package_missing_references.json",
                  "^Error opening file "
                  "\[(.+)tests/data/bundle/marathon\.json\]: No such file or directory")


def test_package_reference_does_not_match_schema():
    _failure_test("tests/data/bundle/package_reference_does_not_match_schema.json",
                  "^Error validating package: "
                  "\[(.+)tests/data/bundle/resource-bad\.json\] "
                  "does not conform to the specified schema")


def test_package_no_match_schema():
    _failure_test("tests/data/bundle/package_no_match_schema.json",
                  "^Error validating package: "
                  "\[(.+)tests/data/bundle/package_no_match_schema\.json\] does not conform to the specified schema")
