# DC/OS Command Line Interface

The DC/OS Command Line Interface (CLI) is a cross-platform command line
utility that provides a user-friendly yet powerful way to manage DC/OS
clusters.

## Installation and usage

If you're a **user** of DC/OS, please follow the [installation
instructions](https://docs.d2iq.com/mesosphere/dcos/latest/cli/install/). Otherwise,
follow the instructions below to set up your development environment.

Detailed help and usage information is available through the dcos help
command and for specific subcommands through `dcos <subcommand> --help`.

Additional documentation for the CLI and for the DC/OS in general is
available in the [DC/OS docs](https://dcos.io/docs/).

## Development setup

### Requirements

1.  [git](http://git-scm.com) must be installed to download the source
    code for the DC/OS CLI.
2.  [go](https://golang.org/dl/) 1.12+ or Docker.
3.  [win-bash](https://sourceforge.net/projects/win-bash/files/shell-complete/latest)
   must be installed if you are using Windows in order to run setup scripts
   from the Makefile.

### Instructions

1.  Clone git repo for the dcos cli:

        git clone git@github.com:dcos/dcos-cli.git

2.  Change directory to the repo directory:

        cd dcos-cli

3.  Build the binary (using Docker):

        make

    or Using Go (1.12+):

        export NO_DOCKER=1
        make

## Using the DC/OS CLI

The DC/OS CLI will be built in the directory `build/<platform>/`.

## Running tests

### Unit tests

    make test

### Integration tests

You need to have a running DC/OS cluster in order to run the integration tests.
Using a Python virtual environment is recommended.

    export DCOS_TEST_DEFAULT_CLUSTER_USERNAME=<username to access the cluster>
    export DCOS_TEST_DEFAULT_CLUSTER_PASSWORD=<password to access the cluster>
    export DCOS_TEST_DEFAULT_CLUSTER_HOST=<IP or domain of the cluster>
    cd tests
    pip install -r requirements.txt
    pytest integration

## Releasing

Releasing a new version of the DC/OS CLI is done through an
[automated Jenkins
build](https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/release/)
which is triggered automatically for new tags and on pushes to master.

The latest binaries (built from the latest tag) are published to:

- https://downloads.dcos.io/cli/releases/binaries/dcos/linux/x86-64/latest/dcos
- https://downloads.dcos.io/cli/releases/binaries/dcos/darwin/x86-64/latest/dcos
- https://downloads.dcos.io/cli/releases/binaries/dcos/windows/x86-64/latest/dcos.exe

The testing binaries (built from the master branch continuously) are published to:

- https://downloads.dcos.io/cli/testing/binaries/dcos/linux/x86-64/master/dcos
- https://downloads.dcos.io/cli/testing/binaries/dcos/darwin/x86-64/master/dcos
- https://downloads.dcos.io/cli/testing/binaries/dcos/windows/x86-64/master/dcos.exe

The release proces is described [here](https://github.com/dcos/dcos-cli/blob/master/design/release.md#release-process)

## Contributing

Contributions are always welcome! Please refer to our [contributing guidelines](CONTRIBUTING.md).
