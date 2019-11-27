# Release process

## dcos-cli

In order to release the `DC/OS CLI version X.Y.Z` (where X is the major version, Y the minor
version, and Z the patch version):

- Make sure CHANGELOG.md is up-to-date for the version `X.Y.Z`

- Create a `X.Y.Z` tag and push it to the Github repo

- After a few minutes the tag will appear as job in https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/release/view/tags/, trigger a build for the job (this can be done by clicking the clock icon on the table item, or by opening the job and clicking `Build now`).

- Open a PR to https://github.com/Homebrew/homebrew-core to bump the `dcos-cli` package.
  An example can be seen here: https://github.com/Homebrew/homebrew-core/pull/43775

- Add a new release entry with the changelog in https://github.com/dcos/dcos-cli/releases.
  An example can be seen here: https://github.com/dcos/dcos-cli/releases/tag/1.0.0

## CLI plugins

`dcos-core-cli` and `dcos-enterprise-cli` releases are tied to a specific major and minor
versions of DC/OS, however the patch version is CLI specific.

The `X.Y-patch.Z` version of one of these plugins would be a release for `DC/OS X.Y`. The Z
version is however unrelated to DC/OS, this makes sure we can publish bug and security
fixes for these plugins independently from DC/OS.

For example, the `2.1-patch.5` version would be the 6th patch release for `DC/OS 2.1`.

### dcos-core-cli

In order to release the version `X.Y-patch.Z` of `dcos-core-cli`:

- Make sure CHANGELOG.md is up-to-date for the version `X.Y-patch.Z`

- Create a `X.Y-patch.Z` tag and push it to https://github.com/dcos/dcos-core-cli.

- After a few minutes the tag will appear as job in https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/core/job/build/view/tags/,
  trigger a build for the job (this can be done by clicking the clock icon on the table item,
  or by opening the job and clicking `Build now`).

- Follow the steps below to release the plugin to the Universe and to the Bootstrap Registry.

### dcos-enterprise-cli

In order to release the version `X.Y-patch.Z` of `dcos-core-cli`:

- Create a `X.Y-patch.Z` tag and push it to https://github.com/mesosphere/dcos-enterprise-cli.

- After a few minutes the tag will appear as job in https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/enterprise/job/publish/view/tags/,
  trigger a build for the job (this can be done by clicking the clock icon on the table item,
  or by opening the job and clicking `Build now`).

- Follow the steps below to publish the plugin to the Universe and to the Bootstrap Registry.

### Release a plugin to the Universe

In order to release a plugin to the Universe, open a PR against https://github.com/mesosphere/universe.

An example of this can be found here: https://github.com/mesosphere/universe/pull/2379

It is possible to auto-generate the `resource.json` file using the `ci/generate_universe_resource.py`
helper script:

``` shell
$ ./generate_universe_resource.py "https://downloads.dcos.io/cli/releases/plugins/dcos-core-cli/{platform}/x86-64/dcos-core-cli-2.0-patch.2.zip"
```

### Release a plugin to the Bootstrap Registry

Once a plugin is released in the Universe (the PR is merged), it can be released in the Bootstrap Registry as
well. This is useful for air-gapped customers.

In order to do so, open a PR to dcos-enterprise which bumps the plugin version in the Bootstrap Registry.
See https://github.com/mesosphere/dcos-enterprise/pull/6580 for example.

The plugin package URL and sha1sum can be found at https://downloads.mesosphere.com/universe/packages/packages.html.

# Updating the used development version

This refers to the action of creating a new branch based on the master branch and then bumping the DC/OS version in the master branch, e.g. https://github.com/dcos/dcos/commit/da1be1a3851c5f85fd3613396b2b0ef11051d058 where a 2.0 branch got created and the DC/OS dev version was updated to 2.1.0-dev.

## Scenario: DC/OS 2.2 is the new DC/OS dev version

### dcos-core-cli

Create a new branch 2.2-patch.x (based on 2.1-patch.x) in https://github.com/dcos/dcos-core-cli.

In the 2.1-patch.x branch, the integration tests Jenkinsfiles need to be updated to use the 2.1 DC/OS installer instead of the master DC/OS installer. Such a change can be seen in https://github.com/dcos/dcos-core-cli/commit/c0ebd5f1e7789f0b49f3e06c6933c81d7e2039cb.

CLI nightly integration tests need to be updated to run the 2.2-patch.x branch (the new dev version). In https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/core/job/integration-tests-nightly/configure, go to Pipeline > Definition > SCM > Branches to build > Branch Specifier (blank for `any`) and update the field to `refs/heads/2.2-patch.x`.

In the following jobs, update the sha1 string parameter to 2.2-patch.x :

- https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/core/job/integration-tests-linux/configure

- https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/core/job/integration-tests-mac/configure

- https://jenkins.mesosphere.com/service/jenkins/job/public-dcos-cluster-ops/job/mesosphere-dcos-cli/job/core/job/integration-tests-windows/configure

### dcos-enterprise-cli

Create a 2.2-patch.x branch in https://github.com/mesosphere/dcos-enterprise-cli.
