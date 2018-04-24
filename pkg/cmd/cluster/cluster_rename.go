package cluster

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdClusterRename renames a cluster.
func newCmdClusterRename(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "rename",
		Args: cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			conf, err := ctx.ConfigManager().Find(args[0], false)
			if err != nil {
				return err
			}
			conf.Set("cluster.name", args[1])
			return conf.Persist()
		},
	}
	return cmd
}
