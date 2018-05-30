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

## Plugin Completion Metadata ##

Completion data will be taken from a structure in the metadata files that encodes the command tree including
arguments, flags, and subcommands along with some of their associated metadata.

Command schema:
```yaml
- name: marathon
  description: ""
  flags: []
  args: []
  subcommands: []
```

Flags schema
```yaml
# ...
flags:
- name: app-version
  shorthand: ""
  type: marathon_app_version
  description: |
    A flag for something
# ...
```
Flag types:
* `boolean`: boolean value that will be set to true if it's there, false otherwise.
* `string`: arbitrary string value
* `_`: custom type like `marathon_app` that can be given to some `<plugin binary> __autocomplete-func__` command
to get custom completions.

Args schema:
```yaml
# ...
args:
- name: app-resource
  description: ""
  type: file
  multiple: false
# ...
```

Arg types:
* `file`: file from filesystem
* `string`: standard string input, no special handling.
* `_`: custom type like `marathon_app` that can be given to some `<plugin binary> __autocomplete-func__` command
to get custom completions.


Using some `marathon` commands as an example, the metadata will go in `plugin.json` or maybe next to it:

```yaml
name: marathon
flags:
- name: config-schema
  type: boolean

# help, version, and info should probably all be implicitly created somehow since I think they'll
# be on every command. Omitting version and info here but leaving help for demonstration
- name: help
  shorthand: h
  type: boolean

subcommands:
- name: about
- name: app
  subcommands:   
    - name: add
      description: add task
      args:
      - name: app-resource
        type: file
        multiple: false

    - name: list
      flags:
      - name: json
        description: |
          print as json
        type: boolean
      - name: quiet
        description: provides no output(?)
        type: boolean
    # ...
      - name: show
        description: show information about a task I think
        args:
        - name: app-id
          type: custom
          multiple: false
          custom_func: marathon_app_id
        flags:
        - name: app-version
          description: show task description from certain version of task
          # this will probably need to somehow take a parameter to be useful
          type: marathon_app_version
```