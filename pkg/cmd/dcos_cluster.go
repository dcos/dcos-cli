package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdCluster creates the `dcos cluster` subcommand.
func newCmdCluster(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "cluster",
	}
	cmd.AddCommand(
		newCmdClusterRemove(ctx),
	)
	return cmd
}
