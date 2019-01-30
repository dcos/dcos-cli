from .common import exec_cmd, default_cluster  # noqa: F401


def test_install_certified_packages_cli(default_cluster):
    pkgs = [
        'cassandra',
        'kubernetes',
    ]

    for pkg in pkgs:
        code, _, _ = exec_cmd(['dcos', 'package', 'install', '--cli', '--yes', pkg])
        assert code == 0
