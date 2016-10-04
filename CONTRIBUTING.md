# Contribution Guide for the DC/OS CLI

Thanks for contributing! Here are a few guidelines to get you started.

## Submitting Issues

Please file feature requests and bugs through Github issues.

If you are submitting a bug report, please include:
- dcos cli version: `dcos --version`
- DC/OS version
- operating system
- command that errored with `--log-level=debug --debug`

## Creating PRs

### Commit Message
Please describe the problem you are addressing and your proposed solution.

### Style
We follow [pep8](https://www.python.org/dev/peps/pep-0008/) and [isort](
https://pypi.python.org/pypi/isort) conventions. You can make sure you follow these by running
`tox -e py34-syntax` in the `dcos-cli` and `cli` directories.

### Tests
Please include test(s) with your changes. Make sure to separate integration and unit tests. Please
use our test helpers for [integration tests](
https://github.com/mesosphere/dcos-cli/blob/master/cli/tests/integrations/common.py) and
[unit tests](https://github.com/mesosphere/dcos-cli/blob/master/cli/tests/unit/common.py)
We run all tests on every PR, and won't look at a PR until all tests pass. Please see
[Running Tests](https://github.com/mesosphere/dcos-cli#running-tests) on how to run our tests
locally.


## Thanks!

The DC/OS CLI Team
