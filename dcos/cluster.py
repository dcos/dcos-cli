import contextlib
import os
import re
import shutil
import ssl
import urllib

from urllib.request import urlopen

import requests

from dcos import config, constants, http, util
from dcos.errors import DCOSException


logger = util.get_logger(__name__)

STATUS_AVAILABLE = 'AVAILABLE'
STATUS_UNCONFIGURED = 'UNCONFIGURED'
STATUS_UNAVAILABLE = 'UNAVAILABLE'

VERSION_UNKNOWN = 'N/A'


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
        res = http.get(cluster_url)
        cluster_id = res.json().get("CLUSTER_ID")

    # don't move cluster if dcos_url is not valid
    except DCOSException as e:
        logger.error(
            "Error trying to find cluster id: {}".format(e))
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
        # This is an informational request,
        # a 5 seconds read timeout is enough.
        res = http.get(cluster_url, timeout=5)
        cluster_id = res.json().get("CLUSTER_ID")

    except DCOSException as e:
        msg = ("Error trying to find cluster id: {}\n "
               "Please make sure the provided DC/OS URL is valid: {}".format(
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

    cluster = Cluster(cluster_id)
    config_path = cluster.get_config_path()
    if stored_cert:
        cert_path = os.path.join(cluster_path, "dcos_ca.crt")
        config.set_val("core.ssl_verify", cert_path, config_path=config_path)

    cluster_name = cluster_id
    try:
        url = dcos_url.rstrip('/') + '/mesos/state-summary'
        # This is an informational request,
        # a 5 seconds read timeout is enough.
        name_query = http.get(url,
                              toml_config=cluster.get_config(),
                              timeout=5)
        cluster_name = name_query.json().get("cluster")

    except DCOSException:
        pass

    config.set_val("cluster.name", cluster_name, config_path=config_path)

    return cluster_path


def get_attached_cluster():
    """
    Get the attached cluster.

    :returns: the attached cluster
    :rtype: Cluster
    """

    clusters = get_clusters()
    for c in clusters:
        if c.is_attached():
            return c

    # If there is only one cluster, set it as attached. This is consistent
    # with config.get_attached_cluster_path().
    if len(clusters) == 1:
        c = clusters[0]
        set_attached(c.get_cluster_path())
        return c


def set_attached(cluster_path):
    """
    Set the cluster specified in `cluster_path` as the attached cluster

    :param cluster_path: path to cluster directory
    :type cluster_path: str
    :rtype: None
    """

    # get currently attached cluster
    attached_cluster_path = config.get_attached_cluster_path()

    if attached_cluster_path and attached_cluster_path != cluster_path:
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

    error_msg = ("Error downloading CA certificate from cluster. "
                 "Please check the provided DC/OS URL.")
    try:
        with urlopen(cert_bundle_url, context=unverified) as f:
            return f.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        # Open source DC/OS does not currently expose its root CA certificate
        if e.code == 404:
            return False
        else:
            logger.debug(e)
            raise DCOSException(error_msg)
    except Exception as e:
        logger.debug(e)
        raise DCOSException(error_msg)


def get_clusters(include_linked=False):
    """
    Get configured or linked clusters.

    :param include_linked: whether to look for linked clusters
    :type include_linked: bool
    :returns: list of Clusters
    :rtype: [Clusters]
    """

    clusters_path = config.get_clusters_path()
    util.ensure_dir_exists(clusters_path)
    clusters = set()

    uuid_regex = re.compile((r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-'
                             r'[89ab][a-f0-9]{3}-[a-f0-9]{12}\Z'))

    for entry in os.listdir(clusters_path):
        entry_path = os.path.join(clusters_path, entry)
        if os.path.isdir(entry_path) and uuid_regex.match(entry):
            c = Cluster(entry)
            clusters.add(c)

    # Search for linked clusters after configured clusters, this makes sure
    # the set gives priority to Cluster over LinkedCluster.
    if include_linked:
        try:
            linked_clusters = get_linked_clusters()
            clusters.update(linked_clusters)
        except DCOSException:
            pass

    return list(clusters)


def get_cluster(name):
    """
    :param name: name of cluster
    :type name: str
    :returns: Cluster identified by name or ID, also accepts an initial
              portion of ID if it's unique.
    :rtype: Cluster
    """

    clusters = []

    for cluster in get_clusters(True):
        cluster_id = cluster.get_cluster_id()
        if cluster_id == name:
            return cluster

        if cluster.get_name() == name or cluster_id.startswith(name):
            clusters.append(cluster)

    if len(clusters) > 1:
        msg = ('Multiple clusters matching "{}", '
               'please use the exact cluster ID.')
        raise DCOSException(msg.format(name))

    return next(iter(clusters), None)


def get_cluster_links(dcos_url):
    """
    Get cluster links.

    :param dcos_url: URL of the DC/OS cluster
    :type dcos_url: str
    :returns: list of links
    :rtype: list
    """

    endpoint = urllib.parse.urljoin(dcos_url, '/cluster/v1/links')
    headers = {'Accept': 'application/json'}

    try:
        return http.get(endpoint, headers=headers).json()
    except ValueError:
        raise DCOSException("Can't parse cluster links.")


def get_linked_clusters():
    """
    Get linked clusters.

    :returns: list of linked clusters
    :rtype: [LinkedCluster]
    """

    current_cluster = get_attached_cluster()
    if not current_cluster:
        return []

    links = get_cluster_links(current_cluster.get_url()).get('links')
    linked_clusters = []

    for link in links:
        link = LinkedCluster(
            link.get('url'),
            link.get('id'),
            link.get('name'),
            link.get('login_provider'))

        linked_clusters.append(link)

    return linked_clusters


def remove(name):
    """
    Remove cluster `name` from the CLI.

    :param name: name of cluster
    :type name: str
    :rtype: None
    """

    def onerror(func, path, excinfo):
        raise DCOSException("Error trying to remove cluster")

    cluster = get_cluster(name)
    if cluster:
        shutil.rmtree(cluster.get_cluster_path(), onerror)
        return
    else:
        raise DCOSException("Cluster [{}] does not exist".format(name))


class Cluster():
    """Interface for a configured cluster"""

    def __init__(self, cluster_id):
        self.cluster_id = cluster_id
        self.cluster_path = os.path.join(
            config.get_clusters_path(), cluster_id)

    def get_cluster_path(self):
        return self.cluster_path

    def get_cluster_id(self):
        return self.cluster_id

    def get_config_path(self):
        return os.path.join(self.cluster_path, "dcos.toml")

    def get_config(self, mutable=False):
        return config.load_from_path(self.get_config_path(), mutable)

    def get_name(self):
        return config.get_config_val(
            "cluster.name", self.get_config()) or self.cluster_id

    def get_url(self):
        return config.get_config_val("core.dcos_url", self.get_config())

    def get_dcos_version(self):
        dcos_url = self.get_url()
        if not dcos_url:
            return VERSION_UNKNOWN

        endpoint = dcos_url.rstrip('/') + '/dcos-metadata/dcos-version.json'

        try:
            # This is an informational request,
            # a 5 seconds read timeout is enough.
            resp = requests.request(
                'GET',
                url=endpoint,
                timeout=5,
                verify=False)

            return resp.json().get("version", VERSION_UNKNOWN)
        except Exception as e:
            return VERSION_UNKNOWN

    def is_attached(self):
        cluster_envvar = os.environ.get(constants.DCOS_CLUSTER)
        if cluster_envvar:
            return cluster_envvar in [self.cluster_id, self.get_name()]

        return os.path.exists(os.path.join(
            self.cluster_path, constants.DCOS_CLUSTER_ATTACHED_FILE))

    def get_status(self):
        if self.get_dcos_version() == VERSION_UNKNOWN:
            return STATUS_UNAVAILABLE

        return STATUS_AVAILABLE

    def __eq__(self, other):
        return isinstance(other, Cluster) and \
            other.get_cluster_id() == self.get_cluster_id()

    def __hash__(self):
        return hash(self.cluster_id)

    def dict(self):
        return {
            "cluster_id": self.get_cluster_id(),
            "name": self.get_name(),
            "url": self.get_url(),
            "version": self.get_dcos_version(),
            "attached": self.is_attached(),
            "status": self.get_status(),
        }


class LinkedCluster(Cluster):
    """Representation of a linked cluster"""

    def __init__(self, cluster_url, cluster_id, cluster_name, provider):
        self.cluster_name = cluster_name
        self.cluster_url = cluster_url
        self.provider = provider

        super().__init__(cluster_id)

    def get_name(self):
        return self.cluster_name

    def get_url(self):
        return self.cluster_url

    def is_attached(self):
        if self.get_status() == STATUS_UNCONFIGURED:
            return False

        return super().is_attached()

    def get_status(self):
        if os.path.exists(self.get_cluster_path()):
            return super().get_status()

        return STATUS_UNCONFIGURED

    def get_provider(self):
        return self.provider
