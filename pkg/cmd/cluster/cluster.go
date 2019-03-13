package cluster

import (
	"fmt"

	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// NewCommand creates the `dcos cluster` subcommand.
func NewCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "cluster",
		Short: "Manage your DC/OS clusters",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			fmt.Fprintln(ctx.ErrOut(), cmd.UsageString())
			return fmt.Errorf("unknown command %s", args[0])
		},
	}
	cmd.AddCommand(
		newCmdClusterAttach(ctx),
		newCmdClusterLink(ctx),
		newCmdClusterList(ctx),
		newCmdClusterRemove(ctx),
		newCmdClusterRename(ctx),
		newCmdClusterSetup(ctx),
		newCmdClusterUnlink(ctx),
	)
	return cmd
}
