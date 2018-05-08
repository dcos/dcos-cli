package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func newSubCmdCluster(ctx *cli.Context) subcommand.SubCommand {
	sc := subcommand.NewInternalSubCommand(newCmdCluster(ctx))

	sc.AddSubCommand(
		newSubCmdClusterAttach(ctx),
		newSubCmdClusterList(ctx),
	)
	return sc
}

// newCmdCluster creates the `dcos cluster` subcommand.
func newCmdCluster(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "cluster",
	}
	/*
		cmd.AddCommand(
			newCmdClusterAttach(ctx),
			newCmdClusterList(ctx),
			newCmdClusterRemove(ctx),
			newCmdClusterRename(ctx),
		)
	*/
	return cmd
}
