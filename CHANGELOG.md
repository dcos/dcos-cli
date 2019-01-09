# CHANGELOG

## Next

## 0.7.7

* Features

  * Build the CLI with 1.12-patch.5

## 0.7.6

* Features

  * Build the CLI with 1.12-patch.4

## 0.7.5

* Bugfixes

  * Fixed emitting empty uid value in login credentials

## 0.7.4

* Features

  * Build the CLI with 1.12-patch.3
  * Enable bash completion to be compatible with zsh

* Bugfixes

  * Drop support for DCOS_URL and DCOS_ACS_TOKEN
  * Unset the ACS token config key whenever the DC/OS URL is updated

## 0.7.3

* Features

  * Build the CLI with 1.12-patch.2

* Bugfixes

  * Do not prompt for login provider selection when uid/password is given

## 0.7.2

* Bugfixes

  * Forward exit code from plugins
  * Discard stderr output during bash completion
  * Support bash completion when no cluster is attached
  * Normalize domain in cluster URLs to lowercase (DCOS_OSS-4501)
  * Updated login flow to fix provider selection when uid/password given (DCOS-45239)

## 0.7.1

* Features

  * Build the CLI with 1.12-patch.1 (#1370)

* Bugfixes

  * Skip browser-based login providers on user/pass credentials

## 0.7.0

* Breaking changes

  * Drop support for DCOS_CONFIG, DCOS_CLUSTER_NAME environment variables
  * Remove the --password-env option for login, it now always reads from DCOS_PASSWORD

* Features

  * Introduce a new top-level command to manage plugins
  * Pass cluster specific environment variables when invoking plugins
  * Add support for dcos task attach
  * Send a DC/OS CLI specific User-Agent in HTTP requests
  * Create CLI UX guidelines
  * Add an --unavailable option to dcos cluster remove
  * Add a --name flag to dcos cluster setup
  * Add Metronome job queue functionality
  * Add verbosity CLI option (-v) and deprecate --log-level and --debug
  * Dump HTTP requests and responses body on very verbose mode (-vv)
  * Support DCOS_USERNAME/DCOS_PASSWORD env vars during login
  * Support dcos auth list-providers in OSS clusters
  * Remove SNAPSHOT in favor of the testing build commit hash in dcos --version
  * (EXPERIMENTAL) Extract core commands to a new dcos-core-cli plugin
  * (EXPERIMENTAL) Auto-install dcos-core-cli / dcos-enterprise-cli plugin during cluster setup

* Bugfixes

  * Handle redirects when setting-up a cluster (DCOS_OSS-4099)
  * dcos auth login clears credentials even if canceled (DCOS-12291)
  * Cluster list command is far too slow (DCOS-18297)
  * Print a warning when using the CLI against a non 1.12 cluster (DCOS_OSS-4371)
  * Fix inconsistencies in the main help output (DCOS-16013)
