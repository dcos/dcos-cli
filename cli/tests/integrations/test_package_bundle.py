import contextlib
import glob
import os
import tempfile
import zipfile

from tests.integrations import common

_PACKAGE_NAME_GLOB = '/tmp/cassandra-0.2.0-1-*'


@contextlib.contextmanager
def _clean_package_file(pattern):
    for name in glob.glob(pattern):
        os.remove(name)

    yield

    for name in glob.glob(pattern):
        os.remove(name)


def test_bundle_good_package():
    with _clean_package_file(_PACKAGE_NAME_GLOB):
        returncode, stdout, stderr = common.exec_command(
            ['dcos', 'package', 'bundle', '--output-directory=/tmp',
             'tests/data/package/create-directory'])

        assert returncode == 0
        assert stdout == b''
        assert stderr.decode('utf-8').startswith(
            'Created DCOS Universe package ')

        with zipfile.ZipFile(
                'tests/data/package/cassandra.zip',
                'r') as expected:
            with zipfile.ZipFile(
                    glob.glob(_PACKAGE_NAME_GLOB)[0],
                    'r') as actual:

                for expected_file, actual_file in zip(
                    sorted(
                        expected.infolist(),
                        key=lambda x: x.filename),
                    sorted(
                        actual.infolist(),
                        key=lambda x: x.filename)):
                    assert expected_file.filename == actual_file.filename
                    assert expected_file.file_size == actual_file.file_size


def test_bundle_fail_missing_package_json():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/missing-package-json-directory'],
        returncode=1,
        stderr=(b'The file package.json is required in the package directory '
                b'[tests/data/package/missing-package-json-directory]\n'))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_invalid_package_json():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/invalid-package-json-directory'],
        returncode=1,
        stderr=(b"Error validating JSON file [tests/data/package/"
                b"invalid-package-json-directory/package.json]\n"
                b"Error: missing required property 'version'.\n"))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_invalid_config_json():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/invalid-config-json-directory'],
        returncode=1,
        stderr=(b'Error validating JSON file [tests/data/package/'
                b'invalid-config-json-directory/config.json]\n'
                b'Error: 42 is not valid under any of the given schemas\n'
                b'Path: type\n'
                b'Value: 42\n'))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_invalid_command_json():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/invalid-command-json-directory'],
        returncode=1,
        stderr=(b'Error validating JSON file [tests/data/package/'
                b'invalid-command-json-directory/command.json]\n'
                b'Error: {\'apt-get\': \'invalid command\'} is not valid '
                b'under any of the given schemas\n'
                b'Value: {"apt-get": "invalid command"}\n'))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_overwrite_existing_file():
    with _clean_package_file(_PACKAGE_NAME_GLOB):
        returncode, stdout, stderr = common.exec_command(
            ['dcos', 'package', 'bundle', '--output-directory=/tmp',
             'tests/data/package/create-directory'])

        assert returncode == 0
        assert stdout == b''
        assert stderr.decode('utf-8').startswith(
            'Created DCOS Universe package ')

        common.assert_command(
            ['dcos', 'package', 'bundle', '--output-directory=/tmp',
             'tests/data/package/create-directory'],
            returncode=1,
            stderr='Output file [{}] already exists\n'.format(
                glob.glob(_PACKAGE_NAME_GLOB)[0]).encode('utf-8'))


def test_bundle_fail_extra_files():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/extra-files-directory'],
        returncode=1,
        stderr=(b'Error bundling package. Extra file in package directory '
                b'[tests/data/package/extra-files-directory/extra-file]\n'))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_extra_files_in_assets():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/extra-assets-files-directory'],
        returncode=1,
        stderr=(b'Error bundling package. Extra file in package directory '
                b'[tests/data/package/extra-assets-files-directory/assets/'
                b'extra-file]\n'))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_non_png_icons():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/non-png-icons-directory'],
        returncode=1,
        stderr=(b'Unable to validate [tests/data/package/'
                b'non-png-icons-directory/images/icon-large.png] as a PNG '
                b'file\n'))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_extra_icons():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/extra-icons-directory'],
        returncode=1,
        stderr=(b'Error bundling package. Extra file in package directory '
                b'[tests/data/package/extra-icons-directory/images/non-png]\n')
    )

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_non_png_screenshots():
    common.assert_command(
        ['dcos', 'package', 'bundle', '--output-directory=/tmp',
         'tests/data/package/non-png-screenshots-directory'],
        returncode=1,
        stderr=(b'Unable to validate [tests/data/package/'
                b'non-png-screenshots-directory/images/screenshots/'
                b'non-png.png] as a PNG file\n'))

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_missing_output_directory():
    returncode, stdout, stderr = common.exec_command(
        ['dcos', 'package', 'bundle', '--output-directory=/temp',
         'tests/data/package/create-directory'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.decode('utf-8').startswith(
        'No such file or directory: /temp/cassandra-0.2.0-1-')

    assert not glob.glob(_PACKAGE_NAME_GLOB)


def test_bundle_fail_output_not_directory():
    with tempfile.NamedTemporaryFile() as temp_file:
        returncode, stdout, stderr = common.exec_command(
            ['dcos', 'package', 'bundle',
             '--output-directory={}'.format(temp_file.name),
             'tests/data/package/create-directory'])

        assert returncode == 1
        assert stdout == b''
        assert stderr.decode('utf-8').startswith(
            'Not a directory: {}/cassandra-0.2.0-1-'.format(temp_file.name))

    assert not glob.glob(_PACKAGE_NAME_GLOB)
