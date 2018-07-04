// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cmd/auth"
	"github.com/dcos/dcos-cli/pkg/cmd/cluster"
	"github.com/dcos/dcos-cli/pkg/cmd/completion"
	"github.com/dcos/dcos-cli/pkg/cmd/config"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

// NewDCOSCommand creates the `dcos` command with its `auth`, `config`, and `cluster` subcommands.
func NewDCOSCommand(ctx *cli.Context) *cobra.Command {
	var verbose int
	cmd := &cobra.Command{
		Use: "dcos",
		PersistentPreRun: func(cmd *cobra.Command, args []string) {
			if verbose == 1 {
				// -v sets the logger level to info.
				ctx.Logger().SetLevel(logrus.InfoLevel)
			} else if verbose > 1 {
				// -vv sets the logger level to debug. This also happens for -vvv
				// and above, in such cases we set the logging level to its maximum.
				ctx.Logger().SetLevel(logrus.DebugLevel)
			}
		},
	}

	cmd.PersistentFlags().CountVarP(&verbose, "", "v", "verbosity (-v or -vv)")

	cmd.AddCommand(
		auth.NewCommand(ctx),
		config.NewCommand(ctx),
		cluster.NewCommand(ctx),
	)

	// If a cluster is attached, we get its plugins.
	if cluster, err := ctx.Cluster(); err == nil {
		pluginManager := ctx.PluginManager(cluster.SubcommandsDir())

		pairs := []*completion.CommandPair{}
		for _, p := range pluginManager.Plugins() {
			for _, e := range p.Executables {
				for _, pCmd := range e.Commands {
					executable := filepath.Join(p.BinDir, e.Filename)
					cCmd := pluginCommand(executable, pluginManager, pCmd)
					pairs = append(pairs, &completion.CommandPair{
						Plugin: pCmd,
						Cobra:  cCmd,
					})
					cmd.AddCommand(cCmd)
				}
			}
		}

		cmd.AddCommand(completion.NewCompletionCommand(ctx, pairs))
	}

	return cmd
}

func pluginCommand(executable string, pluginManager *plugin.Manager, c *plugin.Command) *cobra.Command {
	return &cobra.Command{
		Use:                c.Name,
		Short:              c.Description,
		DisableFlagParsing: true,
		SilenceErrors:      true, // Silences error message if command returns an exit code.
		SilenceUsage:       true, // Silences usage information from the wrapper CLI on error.
		RunE: func(cmd *cobra.Command, args []string) error {
			// Prepend the arguments with the commands name so that the
			// executed command knows which subcommand to execute (e.g.
			// `dcos marathon app` would send `<binary> app` without this).
			argsWithRoot := append([]string{c.Name}, args...)

			return pluginManager.Invoke(executable, argsWithRoot)
		},
	}
}
