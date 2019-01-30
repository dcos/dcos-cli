from dcoscli.test.common import exec_command


def test_install_certified_packages_cli():
    pkgs = [
        'cassandra',
        'kubernetes',
    ]

    for pkg in pkgs:
        code, _, _ = exec_command(['dcos', 'package', 'install',
                                   '--cli', '--yes', pkg])
        assert code == 0
