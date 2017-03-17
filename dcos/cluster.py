import contextlib
import os
import shutil

from dcos import config, constants, http, util
from dcos.errors import DCOSException

logger = util.get_logger(__name__)


def move_to_cluster_config():
    """Create a cluster specific config file + directory
    from a global config file. This will move users from global config
    structure (~/.dcos/dcos.toml) to the cluster specific one
    (~/.dcos/clusters/CLUSTER_ID/dcos.toml) and set that cluster as
    the "attached" cluster.

    :rtype: None
    """

    global_config = config.get_global_config()
    dcos_url = config.get_config_val("core.dcos_url", global_config)

    # if no cluster is set, do not move the cluster yet
    if dcos_url is None:
        return

    try:
        # find cluster id
        cluster_url = dcos_url.rstrip('/') + '/metadata'
        res = http.get(cluster_url, timeout=1)
        cluster_id = res.json().get("CLUSTER_ID")

    # don't move cluster if dcos_url is not valid
    except DCOSException as e:
        logger.error(
            "Error trying to find CLUSTER ID. {}".format(e))
        return

    # create cluster id dir
    cluster_path = os.path.join(config.get_config_dir_path(),
                                constants.DCOS_CLUSTERS_SUBDIR,
                                cluster_id)

    util.ensure_dir_exists(cluster_path)

    # move config file to new location
    global_config_path = config.get_global_config_path()
    util.sh_copy(global_config_path, cluster_path)

    # set cluster as attached
    util.ensure_file_exists(os.path.join(
        cluster_path, constants.DCOS_CLUSTER_ATTACHED_FILE))


@contextlib.contextmanager
def setup_directory():
    """
    A context manager for the temporary setup directory created as a
    placeholder before we find the cluster's CLUSTER_ID.

    :returns: path of setup directory
    :rtype: str
    """

    try:
        temp_path = os.path.join(config.get_config_dir_path(),
                                 constants.DCOS_CLUSTERS_SUBDIR,
                                 "setup")
        util.ensure_dir_exists(temp_path)

        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def setup_cluster_config(dcos_url):
    """
    Create a cluster directory for cluster specified in "setup"
    directory.

    :returns: path to cluster specific directory
    :rtype: str
    """

    try:
        # find cluster id
        cluster_url = dcos_url.rstrip('/') + '/metadata'
        res = http.get(cluster_url, timeout=1)
        cluster_id = res.json().get("CLUSTER_ID")

    except DCOSException as e:
        msg = ("Error trying to find CLUSTER ID: {}\n "
               "Please make sure the provided dcos_url is valid: {}".format(
                   e, dcos_url))
        raise DCOSException(msg)

    # create cluster id dir
    cluster_path = os.path.join(config.get_config_dir_path(),
                                constants.DCOS_CLUSTERS_SUBDIR,
                                cluster_id)
    if os.path.exists(cluster_path):
        raise DCOSException("Cluster [{}] is already setup".format(dcos_url))

    util.ensure_dir_exists(cluster_path)

    # move config file to new location
    util.sh_move(config.get_config_path(), cluster_path)

    return cluster_path


def set_attached(cluster_path):
    """
    Set the cluster specified in `cluster_path` as the attached cluster

    :param cluster_path: path to cluster directory
    :type cluster_path: str
    """

    # get currently attached cluster
    attached_cluster_path = config.get_attached_cluster_path()

    if attached_cluster_path is not None:
        # set cluster as attached
        attached_file = os.path.join(
            attached_cluster_path, constants.DCOS_CLUSTER_ATTACHED_FILE)
        try:
            util.sh_move(attached_file, cluster_path)
        except DCOSException as e:
            msg = "Failed to attach cluster: {}".format(e)
            raise DCOSException(msg)

    else:
        util.ensure_file_exists(os.path.join(
            cluster_path, constants.DCOS_CLUSTER_ATTACHED_FILE))
