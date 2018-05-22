# plugin

The plugin system allows users to extend the DC/OS CLI by providing custom subcommands.

A plugin consists of one or multiple subcommands, and various metadata around it (its version,
JSON schemas for subcommand configs, subcommand descriptions and definitions, etc.).

## Plugin structure

In its normalized form, a plugin is essentially a folder with the following structure:

    helloworld/
      bin/
        dcos-hello
        dcos-goodbye
      config/
        hello.json
        goodbye.json
    plugin.json

### bin folder (required)

The main requirement for a plugin is to have a bin folder with the subcommands it provides.

A subcommand is an executable file with the `dcos-{subcommand}` name where `{subcommand}` is
the name of the subcommand. In the example above, the `helloworld` plugin registers the
`dcos hello` and `dcos goodbye` subcommands into the DC/OS CLI.

On Windows, subcommand executables must have the `.exe` extension (eg. `bin\dcos-hello.exe`).

*For legacy reasons, subcommand executables in `env/bin` (or `env\Scripts` on Windows) are also looked-up.*

### config folder (optional)

The DC/OS CLI configuration files are using TOML sections corresponding to subcommands.

A plugin can define JSON schemas for its subcommands configurations.

### plugin.json (optional)

`plugin.json` contains various metadata about the plugin, such as its version and description.

Its schema is the following:

    {
        "name": "helloworld",
        "description": "Greet the world",
        "version": "1.2.3",
        "source": {
          "type": "zip",
          "url": "https://universe.example.com/helloworld-1.2.zip"
        }
    }

*For legacy reasons, the `name`, `description`, and `version` properties can also be read from a `package.json` file.*
