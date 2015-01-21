import pytest
from dcos import config


@pytest.fixture
def conf():
    return {
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    }


def test_unset_property(conf):
    expect = {
        'dcos': {
            'user': 'principal',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {}
    }

    config._unset_property(conf, 'package.repo_uri')

    assert conf == expect


def test_set_property(conf):
    expect = {
        'dcos': {
            'user': 'group',
            'mesos_uri': 'zk://localhost/mesos'
        },
        'package': {
            'repo_uri': 'git://localhost/mesosphere/package-repo.git'
        }
    }

    config._set_property(conf, 'dcos.user', 'group')

    assert conf == expect


def test_get_property(conf):
    config._get_property(conf, 'dcos.mesos_uri') == 'zk://localhost/mesos'
