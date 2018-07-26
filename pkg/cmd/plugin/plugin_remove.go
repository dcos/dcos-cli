package plugin

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdPluginRemove creates the `dcos plugin remove` subcommand.
func newCmdPluginRemove(ctx api.Context) *cobra.Command {
	return &cobra.Command{
		Use:   "remove",
		Short: "Remove a CLI plugin",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cluster, err := ctx.Cluster()
			if err != nil {
				return err
			}
			return ctx.PluginManager(cluster).Remove(args[0])
		},
	}
}
