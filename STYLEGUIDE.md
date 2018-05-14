# DC/OS CLI Style Guide

## Intro
The DC/OS CLI is the main tool used by developers and operators to interact with DC/OS cluster and services running on the clusters. The teams developing features and CLI plugins should build the CLI per this style guide so that we offer a consistent and usable experience to users of DC/OS.

## Naming Commands
* Generally top level commands are single nouns e.g. dcos job, dcos service
* Top level commands are followed by verbs e.g. dcos job create, dcos cluster rename
* Command names should always be a single, lowercase word without spaces, hyphens, underscores, or other word delimiters
* If there is no obvious way to avoid having multiple words, separate with kebab-case e.g. `dcos auth list-providers`

## Inputs

### Actions

* If no action provided then default to showing usage help output
* Try to be consistent with other subcommands; only break convention if necessary
  * Create - Creating a new object aka New, Add
  * Delete - Deleting an object from the system aka Destroy
  * Add - Adding an object that already exists but not creating a new object e.g. adding an existing user to a group
  * Remove - Removing from an object but not deleting e.g. removing a user from a group
  * Show - Show a description or definition aka Describe, Get
  * List - List all objects

### Arguments/Flags

Commands should support the following flags.

* `--help` and `-h` should always output one level of help
* `--version` should always show the version of the plugin
* `--json` outputs JSON
* `--force` and `-f` to force
* `--quiet` and `-q` to silence output
* `-v` and `-vv` for verbose outputs (for verbose and very verbose)
* `--lines=N` to restrict amount of results

Flags may or may not accept a value.

* Flags should have smart defaults when no value is provided
* Support both flags that have values preceded by "=" and values preceded by a space e.g. `dcos <command> <action> --<flag>=<value>` is the same as `dcos <command> <action> --<flag> <value>`

## Prompts

### Destructive Action Confirmations

If a user tries to delete (or destroy) an object we should ask them to confirm.

```
$ dcos backup delete <id>
Are you sure you want to delete this backup? [y/n]
```

Commands should support passing confirmation via a flag `--yes` and `-y` to satisfy scriptability needs.

```
$ dcos backup delete <id> --yes
```

## Outputs

### JSON

* Commands should be able to accept the `--json` flag and output in JSON format
* JSON should be formatted with multi-line and indentation i.e. not one line

### Tables

* Column headings are UPPERCASE
* Table cells lower case
* Strings left aligned
* Integers right aligned
* First column should be the primary identifier e.g. name or ID
* Column heading alignment should match alignment of data
* Default sorting to the primary column; typically A-Z or date/time
* Do not sort by ID, this is usually useless
* 2 spaces between each column

```
$ dcos <command> list
NAME   HOST      TASKS  STATE    CPU  ID
kafka  10.0.2.3      2	RUNNING  1.1  123-456-789
kafka2 10.0.2.3     99	RUNNING  2.0  123-456-789
```

## Help

Only output help for a single level to reduce cognitive load. For example:

```
$ dcos marathon -h
```

Should output help for “marathon” but not levels below that.

```
$ dcos marathon task -h
```

Should output help for “marathon task” but not levels above or below that.

### Help Formatting

Output help in the following format:

```
$ command -h
Description:
    <description>

Usage:
    dcos <command> <action>
    dcos <command> <action>
    …

Examples:
    An optional section of example(s) on how to run the command.

Commands:
    <command>
        <commandDescription>
    <command>
        <commandDescription>
    …

Options:
    --<flag>
        <flagDescription>
    --<flag>
        <flagDescription>
    …
```

### Error Messages

Error messages shouldn’t be too low-level.

``` 
$ dcos cluster setup https://not-reachable.com
Couldn’t reach https://not-reachable.com, is it a DC/OS cluster master node?
```

If users want the low level error messages, they’d need to run the command with the verbose option: 

```
$ dcos -v cluster setup https://not-reachable.com
[ERR] couldn’t download CA certificates : dial tcp: lookup not-reachable.com: no such host
Couldn’t reach https://not-reachable.com, is it a DC/OS cluster master node?
```

## Do and Don't Examples

### ✅ Do

``` 
$ dcos <command> <subcommand>
```

### 🚫 Don't

```
$ dcos <command> --<subcommand>
```

### ✅ Do

``` 
$ dcos <command> -h
<Description>
<Usage>
<Examples>
<Commands>
<Options>
```

### 🚫 Don't

```
$ dcos <command> -h
<Usage>
<Flags>
<Commands>
```

### ✅ Do

``` 
$ dcos cluster setup https://not-reachable.com
Couldn’t reach https://not-reachable.com, is it a DC/OS cluster master node?
```

### 🚫 Don't

```
$ dcos cluster setup https://not-reachable.com
Error: couldn’t download CA certificates : dial tcp: lookup not-reachable.com on 127.0.0.53:53: no such host
```
