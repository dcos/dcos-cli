from dcos import package
from ..common import assert_same_elements


def test_merge_installed_app_req_cli_req():
    _assert_merged_installed(
        merged_keys=['a', 'c'], app_only=True, cli_only=True)


def test_merge_installed_app_req_cli_opt():
    _assert_merged_installed(
        merged_keys=['a', 'b', 'c'], app_only=True, cli_only=False)


def test_merged_installed_app_opt_cli_req():
    _assert_merged_installed(
        merged_keys=['a', 'c', 'd'], app_only=False, cli_only=True)


def test_merged_installed_app_opt_cli_opt():
    _assert_merged_installed(
        merged_keys=['a', 'b', 'c', 'd'], app_only=False, cli_only=False)


def _assert_merged_installed(merged_keys, app_only, cli_only):
    merged = _merged()
    expected_merged = [merged[k] for k in merged_keys]

    actual_merged = package.merge_installed(
        _apps(), _subs(), app_only, cli_only)

    assert_same_elements(expected_merged, actual_merged)


def _apps():
    return [{'name': 'pkg_a', 'appId': '/pkg_a1', 'foo_a': 'bar_a1'},
            {'name': 'pkg_a', 'appId': '/pkg_a2', 'foo_a': 'bar_a1'},
            {'name': 'pkg_b', 'appId': '/pkg_b1', 'foo_b': 'bar_b1'},
            {'name': 'pkg_b', 'appId': '/pkg_b2', 'foo_b': 'bar_b2'},
            {'name': 'pkg_c', 'appId': '/pkg_c1', 'foo_c': 'bar_c1'}]


def _subs():
    return [{'name': 'pkg_a', 'command': {'name': 'pkg_a'}, 'foo_a': 'baz_a'},
            {'name': 'pkg_c', 'command': {'name': 'pkg_c'}, 'foo_c': 'baz_c'},
            {'name': 'pkg_d', 'command': {'name': 'pkg_d'}, 'foo_d': 'baz_d'}]


def _merged():
    return {'a': {'name': 'pkg_a',
                  'command': {'name': 'pkg_a'},
                  'apps': ['/pkg_a1', '/pkg_a2'],
                  'foo_a': 'baz_a'},
            'b': {'name': 'pkg_b',
                  'apps': ['/pkg_b1', '/pkg_b2'],
                  'foo_b': 'bar_b1'},
            'c': {'name': 'pkg_c',
                  'command': {'name': 'pkg_c'},
                  'apps': ['/pkg_c1'],
                  'foo_c': 'baz_c'},
            'd': {'name': 'pkg_d',
                  'command': {'name': 'pkg_d'},
                  'foo_d': 'baz_d'}}
