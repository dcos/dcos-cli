package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdClusterAttach ataches the CLI to a cluster.
func newCmdClusterAttach(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "attach",
		Args: cobra.MaximumNArgs(1),
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
