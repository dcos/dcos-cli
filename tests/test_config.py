import pytest
from dcos.api import config


@pytest.fixture
def conf():
    return config.Toml({
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    })


def test_unset_property(conf):
    expect = config.Toml({
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {}
    })

    del conf['package.repo_uri']

    assert conf == expect


def test_set_property(conf):
    expect = config.Toml({
        'dcos': {
            'user': 'group',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    })

    conf['dcos.user'] = 'group'

    assert conf == expect


def test_get_property(conf):
    conf['dcos.mesos_uri'] == 'zk://localhost/mesos'
