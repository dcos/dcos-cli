# config

The config package manages the DC/OS CLI configuration for a given cluster.

The DC/OS CLI configuration is persisted to the filesystem as a TOML document. In practice it usually lives in the user's home directory, under `~/.dcos/clusters/<cluster-UUID>/dcos.toml`. The configuration can also be read through environment variables. For more information about the DC/OS CLI configuration, please refer to https://docs.mesosphere.com/1.11/cli/command-reference/dcos-config/.

## Goals

The goals of the config package are to :

- Create, Read and Update DC/OS configurations.
- Validate DC/OS configurations.
- Provide a user-friendly struct representing the common DC/OS config keys.

## Implementation

To do so, it exposes 3 structures : **ConfigManager**, **Config**, **Cluster**.

The **Config** struct is the **data source / persistence layer** for a given DC/OS CLI configuration. It uses a TOML file and the environment as data sources. Changes are made in-memory and they can be flushed to the TOML file explicitly.

The **Cluster** struct is a **domain model** for the DC/OS CLI configuration. It contains getters and setters for fields amongst the "core" and "cluster" sections which are commonly used across the CLI.

The **ConfigManager** is the **repository** for DC/OS configurations. It can search and filter configs based on different criterias, like its name or whether is it currently attached. It is also able to create and delete configs.
