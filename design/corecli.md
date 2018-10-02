# corecli

The 0.7 CLI bundles a version of the [core plugin](https://github.com/dcos/dcos-core-cli) compatible with
1.12 clusters.

The CLI will use the bundled plugin in these 2 scenarios:

- **The CLI is not attached to any cluster**, it will display the core commands in the help menu, if a user runs any of them they will see an error message indicating that no cluster is attached.

- **The CLI is attached to a cluster** and there is no `dcos-core-cli` plugin installed. The first time a core command is invoked, the bundled core CLI will get automatically extracted into the plugins dir, the user will see an informational message (`Extracting dcos-core-cli plugin...`), the CLI will then invoke the requested core command and continue normally.

This makes the CLI and the dcos-core-cli plugin behave like a single piece pending reliable methods of
plugin installation in all supported DC/OS configurations. Ensuring that no scripted or manual processes
were negatively impacted by the architectural changes was a design goal.