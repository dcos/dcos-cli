import contextlib
import os
import shutil
import ssl

from urllib.request import urlopen

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


def setup_cluster_config(dcos_url, temp_path, stored_cert):
    """
    Create a cluster directory for cluster specified in "temp_path"
    directory.

    :param dcos_url: url to DC/OS cluster
    :type dcos_url: str
    :param temp_path: path to temporary config dir
    :type temp_path: str
    :param stored_cert: whether we stored cert bundle in 'setup' dir
    :type stored_cert: bool
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

    # move contents of setup dir to new location
    for (path, dirnames, filenames) in os.walk(temp_path):
        for f in filenames:
            util.sh_copy(os.path.join(path, f), cluster_path)

    if stored_cert:
        config.set_val("core.ssl_verify", os.path.join(
            cluster_path, "dcos_ca.crt"))

    cluster_name = cluster_id
    try:
        url = dcos_url.rstrip('/') + '/mesos/state-summary'
        cluster_name = http.get(url, timeout=1).json().get("cluster")
    except DCOSException:
        pass

    config.set_val("cluster.name", cluster_name)

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


def get_cluster_cert(dcos_url):
    """Get CA bundle from specified cluster.

    This is an insecure request.

    :param dcos_url: url to DC/OS cluster
    :type dcos_url: str
    :returns: cert
    :rtype: str
    """

    cert_bundle_url = dcos_url.rstrip() + "/ca/dcos-ca.crt"

    unverified = ssl.create_default_context()
    unverified.check_hostname = False
    unverified.verify_mode = ssl.CERT_NONE
    try:
        with urlopen(cert_bundle_url, context=unverified) as f:
            return f.read().decode('utf-8')
    except Exception as e:
        msg = "Error downloading CA cert from cluster"
        raise DCOSException("{}:\n{}".format(msg, e))


def get_clusters():
    """
    :returns: list of configured Clusters
    :rtype: [{}]
    """

    for (_, dirnames, _) in os.walk(config.get_clusters_path()):
        return [Cluster(cluster_id).dict() for cluster_id in dirnames]


class Cluster():
    """Interface for a configured cluster"""

    def __init__(self, cluster_id):
        self.cluster_id = cluster_id
        self.cluster_path = os.path.join(
            config.get_clusters_path(), cluster_id)

    def get_cluster_id(self):
        return self.cluster_id

    def get_config(self):
        config_file = os.path.join(self.cluster_path, "dcos.toml")
        return config.load_from_path(config_file)

    def get_name(self):
        return config.get_config_val(
            "cluster.name", self.get_config()) or self.cluster_id

    def get_url(self):
        return config.get_config_val("core.dcos_url", self.get_config())

    def get_dcos_version(self):
        dcos_url = self.get_url()
        if dcos_url:
            url = os.path.join(
                self.get_url(), "dcos-metadata/dcos-version.json")
            try:
                resp = http.get(url, timeout=1, toml_config=self.get_config())
                return resp.json().get("version", "N/A")
            except DCOSException:
                pass

        return "N/A"

    def dict(self):
        return {
            "cluster_id": self.get_cluster_id(),
            "name": self.get_name(),
            "url": self.get_url(),
            "version": self.get_dcos_version()
        }
