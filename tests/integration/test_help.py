import os

import pytest

from .common import exec_cmd, default_cluster  # noqa: F401


def test_dcos_help():
    code, out, err = exec_cmd(['dcos'])
    assert code == 0
    assert err == ''
    assert out == '''Usage:
    dcos [command]

Commands:
    auth
        Authenticate to DC/OS cluster
    cluster
        Manage your DC/OS clusters
    config
        Manage the DC/OS configuration file
    help
        Help about any command
    plugin
        Manage CLI plugins

Options:
    --version
        Print version information
    -v, -vv
        Output verbosity (verbose or very verbose)
    -h, --help
        Show usage help

Use "dcos [command] --help" for more information about a command.
'''


@pytest.mark.skipif(os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_VARIANT') != 'open',
                    reason="Not an OSS cluster")
def test_dcos_help_with_default_oss_plugins(default_cluster):
    code, out, err = exec_cmd(['dcos'])
    assert code == 0
    assert err == ''
    assert out == '''Usage:
    dcos [command]

Commands:
    auth
        Authenticate to DC/OS cluster
    calico
        Manage Calico in DC/OS
    cluster
        Manage your DC/OS clusters
    config
        Manage the DC/OS configuration file
    diagnostics
        Create and manage DC/OS diagnostics bundles
    help
        Help about any command
    job
        Deploy and manage jobs in DC/OS
    marathon
        Deploy and manage applications to DC/OS
    node
        View DC/OS node information
    package
        Install and manage DC/OS software packages
    plugin
        Manage CLI plugins
    quota
        Manage DC/OS quotas
    service
        Manage DC/OS services
    task
        Manage DC/OS tasks

Options:
    --version
        Print version information
    -v, -vv
        Output verbosity (verbose or very verbose)
    -h, --help
        Show usage help

Use "dcos [command] --help" for more information about a command.
'''


@pytest.mark.skipif(os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_VARIANT') != 'enterprise',
                    reason="Not an EE cluster")
def test_dcos_help_with_default_ee_plugins(default_cluster):
    code, out, err = exec_cmd(['dcos'])
    assert code == 0
    assert err == ''
    assert out == '''Usage:
    dcos [command]

Commands:
    auth
        Authenticate to DC/OS cluster
    backup
        Access DC/OS backup functionality
    calico
        Manage Calico in DC/OS
    cluster
        Manage your DC/OS clusters
    config
        Manage the DC/OS configuration file
    diagnostics
        Create and manage DC/OS diagnostics bundles
    help
        Help about any command
    job
        Deploy and manage jobs in DC/OS
    license
        Manage your DC/OS licenses
    marathon
        Deploy and manage applications to DC/OS
    node
        View DC/OS node information
    package
        Install and manage DC/OS software packages
    plugin
        Manage CLI plugins
    quota
        Manage DC/OS quotas
    security
        DC/OS security related commands
    service
        Manage DC/OS services
    task
        Manage DC/OS tasks

Options:
    --version
        Print version information
    -v, -vv
        Output verbosity (verbose or very verbose)
    -h, --help
        Show usage help

Use "dcos [command] --help" for more information about a command.
'''
