# Contribution Guide for the DC/OS CLI

Thanks for contributing! Here are a few guidelines to get you started.

## Submitting Issues

Please file feature requests and bugs through Github issues.

If you are submitting a bug report, please include:
- dcos cli version: `dcos --version`
- DC/OS version
- operating system
- command that errored with `-v`

## Creating PRs

### Commit Message

Please describe the problem you are addressing and your proposed solution.

### Style

You can make sure your code conforms to our code style conventions by running
`make lint` directories.

Please also follow our [style guide](design/style.md) when updating user-facing
parts of the CLI.

### Tests

Please include test(s) with your changes. Make sure to separate integration and unit tests.

You can use `make test` to run unit tests, in order to run integration tests please follow
[these instructions](https://github.com/dcos/dcos-cli#integration-tests).

## Thanks!

The DC/OS CLI Team
