import mock
import requests

from dcos import errors


def test_dcos_auth_exception_as_string():
    response = mock.create_autospec(requests.Response)
    exception = errors.DCOSAuthenticationException(response)

    assert (str(exception) ==
            "Authentication failed. Please run `dcos auth login`.")


def test_dcos_auth_exception_with_message_as_string():
    response = mock.create_autospec(requests.Response)
    exception = errors.DCOSAuthenticationException(
        response, "custom error message")

    assert str(exception) == "custom error message"
