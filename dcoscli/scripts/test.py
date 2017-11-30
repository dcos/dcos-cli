import os
import pytest

from dcos import config, constants, util
from dcoscli.cluster.main import setup
from dcoscli.test.constants import (DCOS_TEST_URL_ENV, DCOS_TEST_USER_ENV,
                                    DCOS_TEST_PASS_ENV)


with util.tempdir() as tempdir:
    os.environ[constants.DCOS_DIR_ENV] = tempdir

    url = os.environ.get(DCOS_TEST_URL_ENV, 'https://172.17.0.2')
    os.environ[DCOS_TEST_URL_ENV] = url

    user = os.environ.get(DCOS_TEST_USER_ENV, 'admin')
    os.environ[DCOS_TEST_USER_ENV] = user

    password = os.environ.get(DCOS_TEST_PASS_ENV, 'admin')
    os.environ[DCOS_TEST_PASS_ENV] = password

    setup(os.environ[DCOS_TEST_URL_ENV],
            username=os.environ[DCOS_TEST_USER_ENV],
            password_env=DCOS_TEST_PASS_ENV,
            no_check=True)

    #pytest -vv --cov=dcos_cli --cov-fail-under=100  --cov-report term-missing tests/
    pytest.main(['-vv', 'tests/'])
