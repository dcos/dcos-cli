# DC/OS CLI [![Build Status](https://travis-ci.org/bamarni/dcos_cli.svg?branch=master)](https://travis-ci.org/bamarni/dcos_cli) [![Build status](https://ci.appveyor.com/api/projects/status/ror139vyj2vy5xt7?svg=true)](https://ci.appveyor.com/project/bamarni/dcos-cli)

The DC/OS Command Line Interface (CLI) is a cross-platform command line utility that provides a user-friendly yet powerful way to manage DC/OS clusters.

## Installation

## Usage

## Development environment

### Requirements

This package requires Python 3.6 and pip.

While not strictly required, make is also recommended and used for documenting how to build and test this package. As an alternative you can directly run the commands specified in Makefile targets.

### Virtual environment

We recommend setting-up a virtual environment, there are various ways to do it. The simplest one being to use the built-in [venv](https://docs.python.org/3/library/venv.html) module :

    # Creates a virtualenv inside an env directory
    python3.6 -m venv env
    # Activates the virtualenv
    source env/bin/activate

### Installing dependencies

The last step is to install development dependencies :

    make deps

You should now be able to invoke the `dcos` command.

## Running tests

Once you have the development environment setup, you can run tests with the following command :

    make test

## Building the dcos binary

In order to build the `dcos` binary, run the following command :

    make build

The binary will then be available at `./dist/dcos` (or `./dist/dcos.exe` on Windows).
