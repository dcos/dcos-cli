# CHANGELOG

## 0.8.0

* Breaking changes
  * Drop support of DCOS_URL and DCOS_ACS_TOKEN

* Features
  * Add static tab completion
  * Introduce a strict deprecation mode (DCOS_CLI_STRICT_DEPRECATIONS=1)
  * Display variant when running `dcos --version`
  * Always auto-install core and EE plugins when running `dcos cluster setup`
  * Add support for relative DCOS_DIR
  * List commands of each plugin alphabetically when running `dcos plugin list`

Alongside we're releasing a new core CLI plugin for DC/OS 1.13, which features:
  * Add color support to `dcos node log`
  * Add a public IP field to `dcos node list`
  * Add `--user` flag to `dcos service log`
  * Add journalctl format options to `dcos node log`: `json-pretty`, `json`, `cat`, `short`
