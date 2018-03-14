import collections
import contextlib
import time

from urllib.parse import urlparse

import retrying

from dcos import mesos
from .common import assert_command, exec_command
from .marathon import add_app, count_apps, watch_all_deployments
from .service import get_services, service_shutdown


@contextlib.contextmanager
def package(package_name, deploy=False, args=[]):
    """Context manager that deploys an app on entrance, and removes it on
    exit.

    :param package_name: package name
    :type package_name: str
    :param deploy: If True, block on the deploy
    :type deploy: bool
    :rtype: None
    """

    nb_apps_before_install = count_apps()
    package_install(package_name, deploy, args)
    try:
        yield
    finally:
        command = ['dcos', 'package', 'uninstall', package_name, '--yes']
        returncode, _, _ = exec_command(command)
        assert returncode == 0
        watch_all_deployments()

        @retrying.retry(wait_fixed=1000, stop_max_attempt_number=300)
        def wait_for_app_count():
            assert count_apps() == nb_apps_before_install

        wait_for_app_count()

        services = get_services()
        for framework in services:
            if framework['name'] == package_name:
                service_shutdown(framework['id'])


UNIVERSE_REPO = "https://universe.mesosphere.com/repo"
UNIVERSE_TEST_REPOS = collections.OrderedDict(
    [
        (
            "helloworld-universe",
            "http://helloworld-universe.marathon.mesos:8086/repo"
        )
    ]
)


def setup_universe_server():
    # Add test repos to Marathon and Cosmos
    for name, url in UNIVERSE_TEST_REPOS.items():
        add_app('tests/data/' + name + '.json', False)
        watch_all_deployments()

        # wait for DNS records for the universe app to be propagated
        host = urlparse(url).netloc
        for i in range(30):
            for record in mesos.MesosDNSClient().hosts(host):
                if record['host'] == host and record['ip'] != '':
                    break
            time.sleep(1)

        assert_command(['dcos', 'package', 'repo', 'add', name, url])


def teardown_universe_server():
    # Remove the test Universe repos from Cosmos and Marathon
    for name, url in UNIVERSE_TEST_REPOS.items():
        assert_command(['dcos', 'package', 'repo', 'remove', name])
        assert_command(
            ['dcos', 'marathon', 'app', 'remove', '/' + name, '--force'])

    watch_all_deployments()


def package_install(package, deploy=False, args=[]):
    """ Calls `dcos package install`

    :param package: name of the package to install
    :type package: str
    :param deploy: whether or not to wait for the deploy
    :type deploy: bool
    :param args: extra CLI args
    :type args: [str]
    :rtype: None
    """

    returncode, _, stderr = exec_command(
        ['dcos', 'package', 'install', '--yes', package] + args)

    assert returncode == 0
    assert stderr == b''

    if deploy:
        watch_all_deployments()


def package_uninstall(package_name, args=[]):
    """ Calls `dcos package uninstall`

    :param package_name: name of the package to uninstall
    :type package_name: str
    :param args: extra CLI args
    :type args: [str]
    :rtype: None
    """

    returncode, _, _ = exec_command(
        ['dcos', 'package', 'uninstall', package_name, '--yes'] + args)
    assert returncode == 0
