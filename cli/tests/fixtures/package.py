def package_fixture():
    """ DC/OS package fixture.

    :rtype: dict
    """

    return {
        "apps": [
            "/helloworld"
        ],
        "command": {
            "name": "helloworld"
        },
        "description": "Example DCOS application package",
        "maintainer": "support@mesosphere.io",
        "name": "helloworld",
        "packageSource":
        "https://github.com/mesosphere/universe/archive/master.zip",
        "postInstallNotes": "A sample post-installation message",
        "preInstallNotes": "A sample pre-installation message",
        "releaseVersion": "0",
        "tags": [
            "mesosphere",
            "example",
            "subcommand"
        ],
        "version": "0.1.0",
        "website": "https://github.com/mesosphere/dcos-helloworld"
    }


def search_result_fixture():
    """ DC/OS package search result fixture.

    :rtype: dict
    """

    return {"packages": [
        {
            "currentVersion": "0.1.0-SNAPSHOT-447-master-3ad1bbf8f7",
            "description": "Apache Cassandra running on Apache Mesos",
            "framework": True,
            "name": "cassandra",
            "tags": [
                "mesosphere",
                "framework"
            ],
            "versions": [
                "0.1.0-SNAPSHOT-447-master-3ad1bbf8f7"
            ]
        },
        {
            "currentVersion": "2.3.4",
            "description": ("A fault tolerant job scheduler for Mesos " +
                            "which handles dependencies and ISO8601 " +
                            "based schedules."),
            "framework": True,
            "name": "chronos",
            "tags": [
                "mesosphere",
                "framework"
            ],
            "versions": [
                "2.3.4"
            ]
        },
        {
            "currentVersion": "0.1.1",
            "description": ("Hadoop Distributed File System (HDFS), " +
                            "Highly Available"),
            "framework": True,
            "name": "hdfs",
            "tags": [
                "mesosphere",
                "framework",
                "filesystem"
            ],
            "versions": [
                "0.1.1"
            ]
        },
        {
            "currentVersion": "0.1.0",
            "description": "Example DCOS application package",
            "framework": False,
            "name": "helloworld",
            "tags": [
                "mesosphere",
                "example",
                "subcommand"
            ],
            "versions": [
                "0.1.0"
            ]
        },
        {
            "currentVersion": "0.9.0-beta",
            "description": "Apache Kafka running on top of Apache Mesos",
            "framework": True,
            "name": "kafka",
            "tags": [
                "mesosphere",
                "framework",
                "bigdata"
            ],
            "versions": [
                "0.9.0-beta"
            ]
        },
        {
            "currentVersion": "0.8.1",
            "description": ("A cluster-wide init and control system for " +
                            "services in cgroups or Docker containers."),
            "framework": True,
            "name": "marathon",
            "tags": [
                "mesosphere",
                "framework"
            ],
            "versions": [
                "0.8.1"
            ]
        },
        {
            "currentVersion": "1.4.0-SNAPSHOT",
            "description": ("Spark is a fast and general cluster " +
                            "computing system for Big Data"),
            "framework": True,
            "name": "spark",
            "tags": [
                "mesosphere",
                "framework",
                "bigdata"
            ],
            "versions": [
                "1.4.0-SNAPSHOT"
            ]
        }
    ]
    }
