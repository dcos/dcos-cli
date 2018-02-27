import os
import shutil

from unittest.mock import MagicMock

import pytest

from mock import Mock, patch
from test_util import add_cluster_dir, create_global_config, env

from dcos import auth, cluster, config, constants, errors, util


def _cluster(cluster_id):
    c = cluster.Cluster(cluster_id)
    c.get_name = MagicMock(return_value="cluster-{}".format(cluster_id))
    return c


def _linked_cluster(cluster_id):
    return cluster.LinkedCluster(
        cluster_url='https://example.org',
        cluster_id=cluster_id,
        cluster_name="It's me, Mario!",
        provider=auth.AUTH_TYPE_OIDC_AUTHORIZATION_CODE_FLOW,
    )


def _test_cluster_list():
    return [_cluster("a"), _cluster("b"), _cluster("c")]


@patch('dcos.cluster.get_clusters')
def test_get_cluster(get_clusters):
    clusters = [_cluster("its_me_mario"), _cluster("its_me_luigi")]
    get_clusters.return_value = clusters

    expected_msg = ('Multiple clusters matching "cluster-its_me", '
                    'please use the cluster ID.')
    with pytest.raises(errors.DCOSException, message=expected_msg):
        assert cluster.get_cluster("its_me")

    assert cluster.get_cluster("cluster-its_me_mario") == clusters[0]
    assert cluster.get_cluster("its_me_m") == clusters[0]
    assert cluster.get_cluster("its_me_mario") == clusters[0]

    assert cluster.get_cluster("cluster-its_me_luigi") == clusters[1]
    assert cluster.get_cluster("its_me_l") == clusters[1]
    assert cluster.get_cluster("its_me_luigi") == clusters[1]

    assert cluster.get_cluster("cluster-its_not_me") is None


def test_get_clusters():
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        # no config file of any type
        assert cluster.get_clusters() == []

        # cluster dir exists, no cluster
        clusters_dir = os.path.join(tempdir, constants.DCOS_CLUSTERS_SUBDIR)
        util.ensure_dir_exists(clusters_dir)
        assert cluster.get_clusters() == []

        # a valid cluster
        cluster_id = "a8b53513-63d4-4059-8b08-fde4fe1f1a83"
        add_cluster_dir(cluster_id, tempdir)

        # Make sure clusters dir can contain random files / folders
        # cf. https://jira.mesosphere.com/browse/DCOS_OSS-1782
        util.ensure_file_exists(os.path.join(clusters_dir, '.DS_Store'))
        util.ensure_dir_exists(os.path.join(clusters_dir, 'not_a_cluster'))

        assert cluster.get_clusters() == [_cluster(cluster_id)]


@patch('dcos.cluster.get_linked_clusters')
def test_get_clusters_with_configured_link(get_linked_clusters):
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir
        cluster_id = "a8b53513-63d4-4059-8b08-fde4fe1f1a83"
        add_cluster_dir(cluster_id, tempdir)
        get_linked_clusters.return_value = [_linked_cluster(cluster_id)]

        clusters = cluster.get_clusters(True)
        assert len(clusters) == 1
        assert type(clusters[0]) == cluster.Cluster


def test_set_attached():
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        cluster_path = add_cluster_dir("a", tempdir)
        # no attached_cluster
        assert cluster.set_attached(cluster_path) is None
        assert config.get_attached_cluster_path() == cluster_path

        cluster_path2 = add_cluster_dir("b", tempdir)
        # attach cluster already attached
        assert cluster.set_attached(cluster_path2) is None
        assert config.get_attached_cluster_path() == cluster_path2

        # attach cluster through environment
        os.environ[constants.DCOS_CLUSTER] = "a"
        assert config.get_attached_cluster_path() == cluster_path

        # attach back to old cluster through environment
        os.environ[constants.DCOS_CLUSTER] = "b"
        assert config.get_attached_cluster_path() == cluster_path2


@patch('dcos.http.get')
def test_setup_cluster_config(mock_get):
    with env(), util.tempdir() as tempdir:
        real_config_dir = config.get_config_dir_path()
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        try:
            setup_temp = os.path.join(config.get_config_dir_path(),
                                      constants.DCOS_CLUSTERS_SUBDIR,
                                      "setup")
            util.ensure_dir_exists(setup_temp)

            cluster_id = "b63fb196-8e9e-43b2-bcda-9771fc1d10d1"
            mock_resp = Mock()
            mock_resp.json.return_value = {
                "CLUSTER_ID": cluster_id,
                "cluster": cluster_id,
                "links": [],
            }
            mock_get.return_value = mock_resp

            expected_folder = os.path.join(
                real_config_dir, constants.DCOS_CLUSTERS_SUBDIR, cluster_id)
            expected_file = os.path.join(expected_folder, "dcos.toml")
            expected_ca_cert = os.path.join(expected_folder, "dcos_ca.crt")

            path = cluster.setup_cluster_config("fake_url", real_config_dir,
                                                setup_temp, True)
            os.environ[constants.DCOS_DIR_ENV] = real_config_dir

            assert path == expected_folder
            assert os.path.exists(path)
            assert os.path.exists(expected_file)

            c = cluster.get_cluster(cluster_id)
            assert c.get_cluster_path() == expected_folder
            assert c.get_cluster_id() == cluster_id
            assert c.get_config().get('core.ssl_verify') == expected_ca_cert
        finally:
            shutil.rmtree(expected_folder)
            assert not os.path.exists(expected_folder)


@patch('dcos.config.get_config_val')
@patch('dcos.http.get')
def test_move_to_cluster_config(mock_get, mock_config):
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        create_global_config(tempdir)
        mock_config.return_value = "fake-url"

        cluster_id = "fake"
        mock_resp = Mock()
        mock_resp.json.return_value = {"CLUSTER_ID": cluster_id}
        mock_get.return_value = mock_resp

        assert config.get_config_dir_path() == tempdir
        cluster.move_to_cluster_config()

        clusters_path = os.path.join(tempdir, constants.DCOS_CLUSTERS_SUBDIR)
        assert os.path.exists(clusters_path)
        cluster_path = os.path.join(clusters_path, cluster_id)
        assert os.path.exists(os.path.join(cluster_path, "dcos.toml"))
        assert os.path.exists(os.path.join(
            cluster_path, constants.DCOS_CLUSTER_ATTACHED_FILE))
