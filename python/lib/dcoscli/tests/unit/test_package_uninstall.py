import dcoscli.package.main as package
import dcoscli.util as util


def test_confirm_uninstall_remove_all_fail_challenge():
    real_read = util._read_response

    def fake_read():
        return "hello-world"

    util._read_response = fake_read
    result = package._confirm_uninstall(_pkg_dict('hello-world'), True, '')
    util._read_response = real_read

    assert result is False


def test_confirm_uninstall_remove_all_pass_challenge():
    real_read = util._read_response

    def fake_read():
        return "uninstall all hello-world"

    util._read_response = fake_read
    result = package._confirm_uninstall(_pkg_dict('hello-world'), True, '')
    util._read_response = real_read

    assert result is True


def test_confirm_uninstall_app_id_fail_challenge():
    real_read = util._read_response

    def fake_read():
        return "hello-world"

    util._read_response = fake_read
    pkg = _pkg_dict('hello-world')
    result = package._confirm_uninstall(pkg, False, 'goodbye')
    util._read_response = real_read

    assert result is False


def test_confirm_uninstall_app_id_pass_challenge():
    real_read = util._read_response

    def fake_read():
        return "goodbye"

    util._read_response = fake_read
    pkg = _pkg_dict('hello-world')
    result = package._confirm_uninstall(pkg, False, 'goodbye')
    util._read_response = real_read

    assert result is True


def test_confirm_uninstall_default_fail_challenge():
    real_read = util._read_response

    def fake_read():
        return "kafka"

    util._read_response = fake_read
    result = package._confirm_uninstall(_pkg_dict('hello-world'), False, '')
    util._read_response = real_read

    assert result is False


def test_confirm_uninstall_default_pass_challenge():
    real_read = util._read_response

    def fake_read():
        return "hello-world"

    util._read_response = fake_read
    result = package._confirm_uninstall(_pkg_dict('hello-world'), False, '')
    util._read_response = real_read

    assert result is True


def test_confirm_uninstall_cli_only():
    real_read = util._read_response

    def fake_read():
        return "hello-world"

    util._read_response = fake_read
    pkg = _pkg_dict('hello-world', app=False)
    result = package._confirm_uninstall(pkg, False, '')
    util._read_response = real_read

    assert result is True


def _pkg_dict(name, app=True, cli=True):
    pkg = {"name": name}
    if app:
        pkg['apps'] = ['/' + name]
    if cli:
        pkg['command'] = {"name": name}

    return pkg
