package cluster

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func NewDcosCmdCluster(ctx *cli.Context) subcommand.DcosCommand {
	sc := subcommand.NewInternalCommand(NewCommand(ctx))

	sc.AddSubCommand(
		newDcosCmdClusterAttach(ctx),
		newDcosCmdClusterList(ctx),
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
