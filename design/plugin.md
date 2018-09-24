# plugin

The CLI plugin system formalizes how users extend the DC/OS CLI with custom subcommands.

A plugin provides one or multiple CLI subcommands, and various metadata around it.

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
