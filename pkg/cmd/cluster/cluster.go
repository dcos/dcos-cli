package cluster

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// NewCommand creates the `dcos cluster` subcommand.
func NewCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "cluster",
	}
	cmd.AddCommand(
		newCmdClusterAttach(ctx),
		newCmdClusterList(ctx),
		newCmdClusterRemove(ctx),
		newCmdClusterRename(ctx),
	)
	return cmd
}
