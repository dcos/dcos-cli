import os

from unittest.mock import MagicMock

import mock
from mock import patch

from test_util import add_cluster_dir, create_global_config, env

from dcos import cluster, config, constants, util


def _cluster(cluster_id):
    c = cluster.Cluster(cluster_id)
    c.get_name = MagicMock(return_value="cluster-{}".format(cluster_id))
    return c


def _test_cluster_list():
    return [_cluster("a"), _cluster("b"), _cluster("c")]


@patch('dcos.cluster.get_clusters')
def test_get_cluster(clusters):
    clusters.return_value = _test_cluster_list()
    assert cluster.get_cluster("a") == _cluster("a")
    assert cluster.get_cluster("cluster-b") == _cluster("b")


def test_get_clusters():
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        # no config file of any type
        assert cluster.get_clusters() == []

        # cluster dir exists, no cluster
        clusters_dir = os.path.join(tempdir, constants.DCOS_CLUSTERS_SUBDIR)
        util.ensure_dir_exists(clusters_dir)
        assert cluster.get_clusters() == []

        # one cluster
        cluster_id = "fake_cluster"
        add_cluster_dir(cluster_id, tempdir)
        assert cluster.get_clusters() == [_cluster(cluster_id)]


def test_set_attached():
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        cluster_path = add_cluster_dir("a", tempdir)
        # no attached_cluster
        assert cluster.set_attached(cluster_path) is None
        assert config.get_attached_cluster_path() == cluster_path

        assert cluster.set_attached(cluster_path) is None
        assert config.get_attached_cluster_path() == cluster_path

        cluster_path2 = add_cluster_dir("b", tempdir)
        # attach cluster already attached
        assert cluster.set_attached(cluster_path2) is None
        assert config.get_attached_cluster_path() == cluster_path2


@patch('dcos.http.get')
def test_setup_cluster_config(mock_get):
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir
        with cluster.setup_directory() as setup_temp:

            cluster.set_attached(setup_temp)

            cluster_id = "fake"
            mock_resp = mock.Mock()
            mock_resp.json.return_value = {
                "CLUSTER_ID": cluster_id,
                "cluster": cluster_id
            }
            mock_get.return_value = mock_resp
            path = cluster.setup_cluster_config("fake_url", setup_temp, False)
            expected_path = os.path.join(
                tempdir, constants.DCOS_CLUSTERS_SUBDIR + "/" + cluster_id)
            assert path == expected_path
            assert os.path.exists(path)
            assert os.path.exists(os.path.join(path, "dcos.toml"))

        assert not os.path.exists(setup_temp)


@patch('dcos.config.get_config_val')
@patch('dcos.http.get')
def test_move_to_cluster_config(mock_get, mock_config):
    with env(), util.tempdir() as tempdir:
        os.environ[constants.DCOS_DIR_ENV] = tempdir

        create_global_config(tempdir)
        mock_config.return_value = "fake-url"

        cluster_id = "fake"
        mock_resp = mock.Mock()
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
