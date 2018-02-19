import os

import pytest

from mock import patch

from test_util import add_cluster_dir, create_global_config, env

from dcos import config, constants, util


@pytest.fixture
def conf():
    return config.Toml(_conf())


def test_get_property(conf):
    conf['dcos.mesos_uri'] == 'zk://localhost/mesos'


def test_get_partial_property(conf):
    conf['dcos'] == config.Toml({
        'user': 'group',
        'mesos_uri': 'zk://localhost/mesos'
    })


def test_iterator(conf):
    assert (sorted(list(conf.property_items())) == [
        ('dcos.mesos_uri', 'zk://localhost/mesos'),
        ('dcos.user', 'principal'),
        ('package.repo_uri', 'git://localhost/mesosphere/package-repo.git'),
    ])


@pytest.fixture
def mutable_conf():
    return config.MutableToml(_conf())


def test_mutable_unset_property(mutable_conf):
    expect = config.MutableToml({
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {}
    })

    del mutable_conf['package.repo_uri']

    assert mutable_conf == expect


def test_mutable_set_property(mutable_conf):
    expect = config.MutableToml({
        'dcos': {
            'user': 'group',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    })

    mutable_conf['dcos.user'] = 'group'

    assert mutable_conf == expect


def test_mutable_test_deep_property(mutable_conf):
    expect = config.MutableToml({
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        },
        'new': {
            'key': 42
        },
    })

    mutable_conf['new.key'] = 42

    assert mutable_conf == expect


def test_mutable_get_property(mutable_conf):
    mutable_conf['dcos.mesos_uri'] == 'zk://localhost/mesos'


def test_mutable_get_partial_property(mutable_conf):
    mutable_conf['dcos'] == config.MutableToml({
        'user': 'group',
        'mesos_uri': 'zk://localhost/mesos'
    })


def test_mutable_iterator(mutable_conf):
    assert (sorted(list(mutable_conf.property_items())) == [
        ('dcos.mesos_uri', 'zk://localhost/mesos'),
        ('dcos.user', 'principal'),
        ('package.repo_uri', 'git://localhost/mesosphere/package-repo.git'),
    ])


def _conf():
    return {
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    }


def test_uses_deprecated_config():
    with env(), util.tempdir() as tempdir:
        os.environ.pop('DCOS_CONFIG', None)
        os.environ[constants.DCOS_DIR_ENV] = tempdir
        assert config.get_config_dir_path() == tempdir

        # create old global config toml
        global_toml = create_global_config(tempdir)
        assert config.get_global_config_path() == global_toml
        assert config.uses_deprecated_config() is True

        # create clusters subdir
        _create_clusters_dir(tempdir)
        assert config.uses_deprecated_config() is False


def test_get_attached_cluster_path():
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        # no clusters dir
        assert config.get_attached_cluster_path() is None

        # clusters dir, no clusters
        _create_clusters_dir(tempdir)
        assert config.get_attached_cluster_path() is None

        # 1 cluster, not attached
        cluster_id = "fake-cluster"
        cluster_path = add_cluster_dir(cluster_id, tempdir)
        assert config.get_attached_cluster_path() == cluster_path
        attached_path = os.path.join(
            cluster_path, constants.DCOS_CLUSTER_ATTACHED_FILE)
        assert os.path.exists(attached_path)

        # attached cluster
        assert config.get_attached_cluster_path() == cluster_path


@patch('dcos.config.load_from_path')
def test_get_config(load_path_mock):
    with env(), util.tempdir() as tempdir:
        os.environ.pop('DCOS_CONFIG', None)
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        # no config file of any type
        # this should create the global config
        config.get_config()
        global_toml = os.path.join(tempdir, "dcos.toml")
        load_path_mock.assert_called_once_with(global_toml, False)
        load_path_mock.reset_mock()

        # create old global config toml
        global_toml = create_global_config(tempdir)
        config.get_config()
        load_path_mock.assert_called_once_with(global_toml, False)
        load_path_mock.reset_mock()

        # clusters dir, no clusters
        _create_clusters_dir(tempdir)
        config.get_config()
        load_path_mock.assert_called_once_with(global_toml, False)
        load_path_mock.reset_mock()

        cluster_id = "fake-cluster"
        cluster_path = add_cluster_dir(cluster_id, tempdir)
        cluster_toml = os.path.join(cluster_path, "dcos.toml")
        config.get_config(True)
        load_path_mock.assert_called_with(cluster_toml, True)


def test_get_cluster_name_ignore_env():
    with env():
        os.environ['DCOS_CLUSTER_NAME'] = 'fake-name'

        cluster_conf = config.Toml({
            'cluster': {'name': 'real-name'},
        })

        cluster_name = config.get_config_val('cluster.name', cluster_conf)

        assert cluster_name == 'real-name'


def _create_clusters_dir(dcos_dir):
    clusters_dir = os.path.join(dcos_dir, constants.DCOS_CLUSTERS_SUBDIR)
    util.ensure_dir_exists(clusters_dir)
