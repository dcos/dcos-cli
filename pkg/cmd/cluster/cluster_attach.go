package cluster

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdClusterAttach ataches the CLI to a cluster.
func newCmdClusterAttach(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "attach",
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			manager := ctx.ConfigManager()
			conf, err := manager.Find(args[0], false)
			if err != nil {
				return err
			}
			return manager.Attach(conf)
		},
	}
	return cmd
}
