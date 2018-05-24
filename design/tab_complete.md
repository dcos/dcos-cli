
# Tab/Auto Completion #

Tab completion is important for creating a CLI that provides a good user experience. This feature
is somewhat nebulous at the moment. There are many aspects to it and the implementation will be
dependent on what's most feasible with the command dispatch framework that we use.

## Goals ##
There are multiple different aspects of tab completion that may or may not make it into the CLI
depending on how feasible they are to implement.

*Must have:*
* Support for bash.
* Subcommand completion, e.g. `dcos cluster[TAB]` should give you `list attach remove rename`.
This includes handling partial completion, e.g. `dcos clu[TAB]` should give you `cluster`. But that will
be easy to do with `compgen`.
* Support for currently existing commands without modification of the code itself.
* Users won't need to update their completion script often. Often in this sense would be whenever
the plugins they have installed have been updated. It's possible that the basic script will need to
be updated ocassionally but this should be rare.

*Nice to have:*
* Support for zsh. While it would be easy to get basic completion working from the bash script,
ideally, we could set up a different completion code path that takes advantage of some of the
additional features provided by zsh.
* Argument completion. This would mean intelligently completing arguments with DC/OS object
identifiers, e.g. `dcos cluster attach[TAB]` would give a list of all clusters the CLI is aware of.
* Flag name completion. Provide completion for flag names available to the current command, e.g.
`dcos auth list-providers --[TAB]` should give `json`.
* Flag argument completion. Provide intelligent completion for flag arguments, e.g.
`dcos node ssh --private-ip=[TAB]` should give a list of the private IPs of all nodes in the cluster.


## Implementation ##

To support a mostly static completion script, we're planning to mimic how the
[Mesos CLI does completion](https://github.com/apache/mesos/blob/master/src/python/cli_new/mesos.bash_completion).
So for DC/OS it would call something like `dcos __autocomplete__ bash dcos cluster list` and much of the completion
will be handled by a command built into the CLI. The leading `bash` would indicate which shell-specific completion
script to execute, it's an argument because users won't be expected to type this regularly since it'll be in the
completion script which is already shell specific.

For commands that exist outside of the CLI, it will work similarly, shelling out to that command if it supports
completion, like `<subcommand binary> __autocomplete__ bash marathon task list`. And if they don't support
`__autocomplete__` then they would need to have some metadata that describes at least some things about the
binary (subcommands, flags, etc.) so the CLI can provide at least a basic completion experience even on older
versions of our plugins.


## Complications ##

We would like to minimize the amount of special consideration required to make our commands support the
various types of autocompletion. For this, it would be ideal to use a CLI framework that allows us to look
at the internals of the commands we've built in order to extract subcommand and flag names. For additional
pieces like argument completion or flag value completion, we're thinking of adding some metadata to the
command/flag objects that the autocomplete command can read to determine what special behavior might be needed.

The current problem that we're running into with Cobra comes from how it handles flags. Parsing flags is
complicated and much of the code to handle it is in private functions within the Cobra package that also
use fields private to Cobra. This makes it extremely difficult to differentiate a flag followed by a
subcommand name and a flag that takes a value, e.g. with `dcos -v cluster list` we would need to check
that `-v` doesn't take a value, therefore `cluster` must be an argument/subcommand. Because of this, it will
be difficult to do robust argument completion or flag value completion.
