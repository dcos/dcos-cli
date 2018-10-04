package plugin

import (
	"errors"

	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdPluginRemove creates the `dcos plugin remove` subcommand.
func newCmdPluginRemove(ctx api.Context) *cobra.Command {
	return &cobra.Command{
		Use:   "remove <plugin>",
		Short: "Remove a CLI plugin",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if args[0] == "dcos-core-cli" {
				return errors.New("the core plugin can't be removed")
			}
			cluster, err := ctx.Cluster()
			if err != nil {
				return err
			}
			return ctx.PluginManager(cluster).Remove(args[0])
		},
	}
}
