import os

from dcos import config, constants, http, util
from dcos.errors import DCOSException

logger = util.get_logger(__name__)


def create_cluster_config():
    """Create a cluster specific config file + directory
    from a global config file. This will move users from global config
    structure (~/.dcos/dcos.toml) to the cluster specific one
    (~/.dcos/clusters/CLUSTER_ID/dcos.toml) and set that cluster as
    the "attached" cluster.

    :rtype: None
    """

    dcos_url = config.get_config_val("core.dcos_url")

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
            "Error trying to find CLUSTER_ID. {}".format(e))
        return

    # create cluster id dir
    cluster_path = os.path.join(config.get_config_dir_path(),
                                constants.DCOS_CLUSTERS_SUBDIR,
                                cluster_id)

    util.ensure_dir_exists(cluster_path)

    # move config file to new location
    global_config_path = config.get_global_config()
    util.sh_copy(global_config_path, cluster_path)

    # set cluster as attached
    util.ensure_file_exists(os.path.join(
        cluster_path, constants.DCOS_CLUSTER_ATTACHED_FILE))
