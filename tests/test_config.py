from dcos import config

import pytest


@pytest.fixture
def conf():
    return config.Toml(_conf())


def test_get_property(conf):
    conf['dcos.mesos_uri'] == 'zk://localhost/mesos'


def test_get_partial_property(conf):
    conf['dcos'] == config.Toml({
        'user': 'group',
        'mesos_uri': 'zk://localhost/mesos'
    })


def test_iterator(conf):
    assert (sorted(list(conf.property_items())) == [
        ('dcos.mesos_uri', 'zk://localhost/mesos'),
        ('dcos.user', 'principal'),
        ('package.repo_uri', 'git://localhost/mesosphere/package-repo.git'),
    ])


@pytest.fixture
def mutable_conf():
    return config.MutableToml(_conf())


def test_mutable_unset_property(mutable_conf):
    expect = config.MutableToml({
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {}
    })

    del mutable_conf['package.repo_uri']

    assert mutable_conf == expect


def test_mutable_set_property(mutable_conf):
    expect = config.MutableToml({
        'dcos': {
            'user': 'group',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    })

    mutable_conf['dcos.user'] = 'group'

    assert mutable_conf == expect


def test_mutable_test_deep_property(mutable_conf):
    expect = config.MutableToml({
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        },
        'new': {
            'key': 42
        },
    })

    mutable_conf['new.key'] = 42

    assert mutable_conf == expect


def test_mutable_get_property(mutable_conf):
    mutable_conf['dcos.mesos_uri'] == 'zk://localhost/mesos'


def test_mutable_get_partial_property(mutable_conf):
    mutable_conf['dcos'] == config.MutableToml({
        'user': 'group',
        'mesos_uri': 'zk://localhost/mesos'
    })


def test_mutable_iterator(mutable_conf):
    assert (sorted(list(mutable_conf.property_items())) == [
        ('dcos.mesos_uri', 'zk://localhost/mesos'),
        ('dcos.user', 'principal'),
        ('package.repo_uri', 'git://localhost/mesosphere/package-repo.git'),
    ])


def _conf():
    return {
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    }
