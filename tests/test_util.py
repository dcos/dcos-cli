import contextlib
import os

import pytest

from dcos import constants, util
from dcos.errors import DCOSException


def test_open_file():
    path = 'nonexistant_file_name.txt'
    with pytest.raises(DCOSException) as excinfo:
        with util.open_file(path):
            pass
    assert 'Error opening file [{}]: No such file or directory'.format(path) \
        in str(excinfo.value)


def test_read_file_secure_with_trailing_newline():
    with util.temptext(b"my_secure_password\n") as temp_file:
        path = temp_file[1]
        os.chmod(path, 0o600)
        password = util.read_file_secure(path)
        assert password == "my_secure_password"


def test_read_file_secure_with_trailing_whitespaces():
    with util.temptext(b"my_secure_password \r\n") as temp_file:
        path = temp_file[1]
        os.chmod(path, 0o600)
        password = util.read_file_secure(path)
        assert password == "my_secure_password"


@contextlib.contextmanager
def env():
    """Context manager for altering env vars in tests """

    try:
        old_env = dict(os.environ)
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def add_cluster_dir(cluster_id, dcos_dir):
    clusters_dir = os.path.join(dcos_dir, constants.DCOS_CLUSTERS_SUBDIR)
    util.ensure_dir_exists(clusters_dir)

    cluster_path = os.path.join(clusters_dir, cluster_id)
    util.ensure_dir_exists(cluster_path)

    os.path.join(cluster_path, "dcos.toml")
    return cluster_path


def create_global_config(dcos_dir):
    global_toml = os.path.join(dcos_dir, "dcos.toml")
    util.ensure_file_exists(global_toml)
    return global_toml
