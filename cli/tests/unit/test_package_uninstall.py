import dcoscli.package.main as package
import dcoscli.util as util


def test_confirm_uninstall_remove_all_fail_challenge():
    real_read = util._read_response

    def fake_read():
        return "hello-world"

    util._read_response = fake_read
    result = package._confirm_uninstall('hello-world', True, '')
    util._read_response = real_read

    assert result is False


def test_confirm_uninstall_remove_all_pass_challenge():
    real_read = util._read_response

    def fake_read():
        return "uninstall all hello-world"

    util._read_response = fake_read
    result = package._confirm_uninstall('hello-world', True, '')
    util._read_response = real_read

    assert result is True


def test_confirm_uninstall_app_id_fail_challenge():
    real_read = util._read_response

    def fake_read():
        return "hello-world"

    util._read_response = fake_read
    result = package._confirm_uninstall('hello-world', False, 'goodbye')
    util._read_response = real_read

    assert result is False


def test_confirm_uninstall_app_id_pass_challenge():
    real_read = util._read_response

    def fake_read():
        return "goodbye"

    util._read_response = fake_read
    result = package._confirm_uninstall('hello-world', False, 'goodbye')
    util._read_response = real_read

    assert result is True


def test_confirm_uninstall_default_fail_challenge():
    real_read = util._read_response

    def fake_read():
        return "kafka"

    util._read_response = fake_read
    result = package._confirm_uninstall('hello-world', False, '')
    util._read_response = real_read

    assert result is False


def test_confirm_uninstall_default_pass_challenge():
    real_read = util._read_response

    def fake_read():
        return "hello-world"

    util._read_response = fake_read
    result = package._confirm_uninstall('hello-world', False, '')
    util._read_response = real_read

    assert result is True
