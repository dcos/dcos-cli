package cluster

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func NewSubCmdCluster(ctx *cli.Context) subcommand.SubCommand {
	sc := subcommand.NewInternalCommand(NewCommand(ctx))

	sc.AddSubCommand(
		newSubCmdClusterAttach(ctx),
		newSubCmdClusterList(ctx),
	)
	return sc
}

// NewCommand creates the `dcos cluster` subcommand.
func NewCommand(ctx api.Context) *cobra.Command {
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
