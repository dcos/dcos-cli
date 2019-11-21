# CHANGELOG

## Next

## 1.1.2

* Fixes

  * Do not consume all input data on prompts.
  * Check TLS configuration before calling plugins.

## 1.1.1

* Fixes

  * Fix panic on non-desktop environments with browser login flows other than auth0

## 1.1.0

* Features

  * Pass plugin config as environment variables.
  * Pass `DCOS_CLI_VERSION` when invoking plugins.
  * Add `--no-timeout` option to `cluster setup`

* Fixes

  * Discard the local login server on non-desktop environment

## 1.0.1

* Fixes

  * Fix `dcos package install dcos-core-cli` error on air-gapped environments.

## 1.0.0

* Breaking changes

  *  Unbundle the dcos-core-cli plugin from the CLI. It is now auto-installed from Cosmos only (either through Universe or the Bootstrap Registry).

* Features

  * New command `dcos config keys` printing all the keys that can be set in a configuration file.
  * The new `dcos cluster open` can be used to open the currently attached cluster UI in the browser.
  * Log into DC/OS Open without copy/pasting authentication token from browser.
  * Add cluster name completion to `dcos cluster rename`.
  * Support arg completion for `dcos config`.
  * Support autocompletion on `dcos plugin remove`.

* Experimental features

  * Auto-install CLI plugins for running services during `dcos cluster setup` when environment variable `DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS` set.

* Fixes

  * Loosen the DC/OS version check for plugin auto-installation, it was only accepting 1.XX versions.
  * Improve error messages for `dcos cluster setup` args error

* Testing

  * Run integration tests against DC/OS Open as well.
