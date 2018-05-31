// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cmd/auth"
	"github.com/dcos/dcos-cli/pkg/cmd/cluster"
	"github.com/dcos/dcos-cli/pkg/cmd/completion"
	"github.com/dcos/dcos-cli/pkg/cmd/config"
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
		completion.NewAutocompleteCommand(ctx),
	)
	return cmd
}
