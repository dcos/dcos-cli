import collections
import contextlib
import time

from .common import assert_command, exec_command
from .marathon import add_app, watch_all_deployments
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

    package_install(package_name, deploy, args)
    try:
        yield
    finally:
        command = ['dcos', 'package', 'uninstall', package_name, '--yes']
        returncode, _, _ = exec_command(command)
        assert returncode == 0
        watch_all_deployments()

        services = get_services()
        for framework in services:
            if framework['name'] == package_name:
                service_shutdown(framework['id'])


UNIVERSE_REPO = "https://universe.mesosphere.com/repo"
UNIVERSE_TEST_REPOS = collections.OrderedDict(
    [
        ("test-universe", "http://universe.marathon.mesos:8085/repo"),
        (
            "helloworld-universe",
            "http://helloworld-universe.marathon.mesos:8086/repo"
        )
    ]
)


def setup_universe_server():
    # add both Unvierse servers with static packages
    add_app('tests/cli/data/universe-v3-stub.json', True)
    add_app('tests/cli/data/helloworld-v3-stub.json', True)

    assert_command(
        ['dcos', 'package', 'repo', 'remove', 'Universe'])

    # Add the two test repos to Cosmos
    for name, url in UNIVERSE_TEST_REPOS.items():
        assert_command(['dcos', 'package', 'repo', 'add', name, url])

    watch_all_deployments()
    # Give the test universe some time to become available
    describe_command = ['dcos', 'package', 'describe', 'helloworld']
    for i in range(30):
        returncode, _, _ = exec_command(describe_command)
        if returncode == 0:
            break
        time.sleep(1)
    else:
        # Explicitly clean up in this case; pytest will not automatically
        # perform teardowns if setup fails. See the remarks at the end of
        # http://doc.pytest.org/en/latest/xunit_setup.html for more info.
        teardown_universe_server()
        assert False, 'test-universe failed to come up'


def teardown_universe_server():
    # Remove the test Universe repos from Cosmos
    for name, url in UNIVERSE_TEST_REPOS.items():
        assert_command(['dcos', 'package', 'repo', 'remove', name])

    assert_command(
        ['dcos', 'package', 'repo', 'add', 'Universe', UNIVERSE_REPO])

    # Remove the Marathon tasks running our two test Universe
    assert_command(
        ['dcos', 'marathon', 'app', 'remove', '/universe', '--force'])
    assert_command(
        ['dcos', 'marathon', 'app', 'remove', '/helloworld-universe',
         '--force']
    )

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

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'install', '--yes', package] + args)

    assert returncode == 0
    assert stderr == b''

    if deploy:
        watch_all_deployments()


def package_uninstall(package_name, args=[], stderr=b''):
    """ Calls `dcos package uninstall`

    :param package_name: name of the package to uninstall
    :type package_name: str
    :param args: extra CLI args
    :type args: [str]
    :param stderr: expected string in stderr for package uninstall
    :type stderr: bytes
    :rtype: None
    """

    assert_command(
        ['dcos', 'package', 'uninstall', package_name, '--yes'] + args,
        stderr=stderr)
