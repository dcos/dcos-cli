# cli

The cli package is the "glue" between CLI commands and other packages.

## Goals

- Facilitate testing by abstracting the environment (stdout/stderr, stdin, env vars, filesystem, current system user, etc.).
- Act as a factory for different structures from various packages.

## Implementation

To satisfy both goals, a Context struct is introduced. It is created based on an Environment (which contains various abstractions for stdout/stderr, the filesystem, etc.).

Once created, the context is passed as an argument to each subcommand constructor and they must use it to interact with the environment (print output, read env vars or files, etc.) or instanciate environment-dependent structs from other packages.
