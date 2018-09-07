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

### Arguments/Options

CLI arguments should follow the [GNU standards][1] as much as possible.

Commonly used options are:

* `--help` and `-h` should always output one level of help
* `--json` outputs JSON
* `--force` and `-f` to force
* `--quiet` and `-q` to silence standard output
* `-v` and `-vv` for verbose outputs on stderr ("verbose" or "very verbose")
* `--lines=N` to restrict amount of results

Please refer to [this table][2] for other common option names.

## Prompts

### Destructive Action Confirmations

If a user tries to delete (or destroy) an object we should ask them to confirm.

```
$ dcos backup delete <id>
Are you sure you want to delete this backup? [y/n]
```

Commands should support passing confirmation via `--yes` and `-y` options to satisfy scriptability needs.

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

Examples:
    An optional section of example(s) on how to run the command.

Commands:
    <command>
        <commandDescription>
    <command>
        <commandDescription>
    …

Options:
    --<option>
        <optionDescription>
    --<option>
        <optionDescription>
    …
```

### Error Messages

In general on success there is no output, this follows a UNIX good practice ("No News Is Good News").
However on errors the CLI must always display an informative message, it shouldn’t be too low-level.

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
<Options>
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

[1]: https://www.gnu.org/software/libc/manual/html_node/Argument-Syntax.html
[2]: https://www.gnu.org/prep/standards/html_node/Option-Table.html#Option-Table