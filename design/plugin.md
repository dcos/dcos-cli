# plugin

The CLI plugin system formalizes how users extend the DC/OS CLI with custom subcommands.

A plugin provides one or multiple CLI subcommands, and various metadata around it.

## Content
- [Plugin Structure](#plugin-structure)
- [Migration from legacy plugins or BIN plugins](#migration-from-legacy-plugins-or-BIN-plugins)
- [Add autocompletion to a plugin](#add-autocompletion-to-a-plugin)

## Plugin structure

In its normalized form, an unpacked plugin is a directory with the following structure:

```
  helloworld/
      env/
        bin/
          dcos-hello
          dcos-goodbye
        plugin.toml
      package.json
```

An unpacked plugin has an env directory containing a bin directory which contains all the executables in
the plugin and a plugin.toml file which defines information about the plugin.

The bin directory is just a convention, it can be changed to something else as we'll see in the next section.

A plugin may contain multiple executables, each of which can hold multiple top level commands. Which
executables hold which top level commands is defined in the plugin.toml file. The file contains command
descriptions and definitions, etc.

On Windows, subcommand executables must have the `.exe` extension.

### plugin.toml

plugin.toml contains various metadata about the plugin, such as its schema version and description.

Its schema is the following:

``` toml
schema_version = 1
name = "helloworld"

[[commands]]
name = "hello"
path = "bin/dcos-hello"
description = "Say Hello"

[[commands]]
name = "hallo"
path = "bin/dcos-hallo"
description = "Say Hallo auf Deutsch"
```

### package.json

The presence of this file indicates that the plugin was installed through the universe (eg. dcos package install kafka --cli).

## dcos plugin add

This new subcommand installs a package or a plugin for the corresponding DC/OS cluster. It is not a package manager, it only takes a path to a file ( ./…) or a URL (http(s)://), downloads the file, and puts it in the correct directory.

It takes the following flags:

- --update: We don’t want to overwrite, if a user adds a plugin that already exists. Instead, an error message should be printed stating that the plugin is already installed. If the user passes the path or URL of an already existing plugin but also adds the flag --update (or -u) flag, we will accept the reinstallation of the plugin.

We define two types of plugins that can be installed: **zip** plugins and **bin** plugins.

### ZIP plugins

ZIP plugins are simply unpacked into the UUID directory of the attached cluster, such as:

```
$ tree ~/.dcos
    \- clusters
        \- 31781309-DD09-4B73-AEA6-05B4A2F6B6FC
            \- subcommands
                \- helloworld (plugin folder, please see “Plugin Structure” section)
```

A ZIP plugin is extracted into the env subfolder. The content of a ZIP plugin might be for example :

```
  bin/
    dcos-hello
    dcos-goodbye
  plugin.toml
```

### BIN plugins

BIN plugins (which only consist of a single binary executable file) are copied into the same location as ZIP plugins. A barebone plugin structure gets created, which only contains an env/bin folder with the single binary. At installation time a BIN plugin doesn’t contain a plugin.toml file. Please see the “Migration from legacy plugins or BIN plugins” section below.

While BIN plugins are not deprecated, they do not support the same set of features as ZIP plugins (eg. the yet-to-come bash autocompletion feature).

## dcos plugin remove

As its name suggests, this command removes plugins (their name being given as arguments) locally by removing their directory from the filesystem.

As the [core CLI is bundled](corecli.md) within the DC/OS CLI, removing the `dcos-core-cli` plugin triggers an error.

## dcos plugin list

This command lists installed plugins, with their name, version, description and the subcommands they provide. It also accepts a --json flag.

## Calling a plugin

When a plugin is called it will have the top level command name as its second argument regardless of whether the plugin only has one executable.

For example, if a `dcos-hello` executable in a plugin has a `hello` top level command, it would be called like `env/bin/dcos-hello hello [...]`.

Executables contained within plugins are called synchronously from the CLI by spawning a new child process. The CLI waits for the child process to complete. The CLI makes available its own executable path to the child via an ENV variable `DCOS_CLI_EXECUTABLE_PATH`.

When a cluster is attached, the CLI will also pass the following ENV variables:

- `DCOS_URL`: The base URL of the DC/OS cluster without a trailing slash (eg. `https://dcos.example.com`).
- `DCOS_ACS_TOKEN`: The authentication token for the current user.
- `DCOS_TLS_INSECURE`: Indicates whether the CLI is configured with an insecure TLS setup. This is set to
                       `1` when the `DCOS_URL` scheme is `http://` or `core.ssl_verify` is set to `false`.
- `DCOS_TLS_CA_PATH`: Unless `DCOS_TLS_INSECURE=1`, this env var indicates the path to the CA bundle to
                      verify server certificates against. When it is not set, the system's CA bundle
                      must be used.

The child process has access to the standard out/standard error of the CLI process. It is not guaranteed to have access to any other file descriptors the parent may have opened.

The child process is not started in a shell. If the command is not startable for any reason an error message is printed (not on the path, executable does not exist, binary incompatibility, etc).

## Migration from legacy plugins or BIN plugins

When loading available plugins, the CLI will first look for a plugin.toml file, if it finds that it will attempt to load the plugin with it. If it does not find plugin.toml, it will create it automatically. It will create it based on the set of conventions currently in DC/OS CLI 0.6 :

- Binary executables names (the basename config option) follow the dcos-{subcommand} pattern.

- Subcommand summaries (the description config option) are retrieved by calling the binary with the ./bin/{basename} {subcommand} --info command.

## Add autocompletion to a plugin

To add completion scripts to a plugin, a `completion/bash` directory needs to be created. Here is the structure of the `dcos-core-cli` plugin:

```
.
├── bin
│   ├── dcos
├── completion
│   └── bash
│     ├── job.sh
│     ├── marathon.sh
│     ├── node.sh
│     ├── package.sh
│     ├── service.sh
│     └── task.sh
└── plugin.toml
```

The `completion/bash` directory contains all the autocompletion scripts for the `dcos-core-cli` and a custom plugin needs the same structure. Completion functions can be defined in one or more files in this directory. All files in the `completion/bash` will be sourced.

To write completion scripts, create bash scripts that contain a completion function for every top-level command of the plugin. E.g., for the `dcos service` command in `dcos-core-cli`:

```bash
_dcos_service() {
    local i command

    if ! __dcos_default_command_parse; then
        return
    fi

    local flags=(
    "--help"
    "--info"
    "--version"
    "--completed"
    "--inactive"
    "--json"
    )

    local commands=(
    "log"
    "shutdown"
    )

    if [ -z "$command" ]; then
        case "$cur" in
            --*)
                __dcos_handle_compreply "${flags[@]}"
                ;;
            *)
                __dcos_handle_compreply "${commands[@]}"
                ;;
        esac
        return
    fi

    __dcos_handle_subcommand
}

```

The naming scheme of the function for the top-level command is _very_ important: `_dcos_<top-level-cmd>()`. This function will be called if `dcos top-level-cmd <tab>` is entered on the command line. If this function does not exist, no further completion logic will be executed. Any further completion logic needs to be called from `_dcos_<top-level-cmd>()`.

It is possible to use functions provided by [`dcos-cli`](https://github.com/dcos/dcos-cli/blob/master/pkg/cmd/completion/completion.sh) (`__dcos_default_command_parse`, `__dcos_handle_compreply`, `__dcos_handle_subcommand`) to write your completion logic since these functions will be available in the same shell session. Or you can create custom completion logic, for example have generated code, as long as there are functions following the naming scheme for the top-level commands that call into that logic.

In `dcos-cli` and `dcos-core-cli` we follow this naming scheme for all top-level commands and subcommands.

For more examples of completion functions, check [`dcos-cli`](https://github.com/dcos/dcos-cli/blob/master/pkg/cmd/completion/completion.sh) and [`dcos-core-cli`](https://github.com/dcos/dcos-core-cli/tree/1.13-patch.x/completion/bash).

How to enable autocompletion for the DC/OS CLI is documented [here](https://docs.mesosphere.com/1.12/cli/autocompletion/). To enable completions for a plugin, it has to be added to the CLI.
