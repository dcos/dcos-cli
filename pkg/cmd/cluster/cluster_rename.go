package cluster

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdClusterRename renames a cluster.
func newCmdClusterRename(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "rename <cluster> <name>",
		Short: "Rename a configured cluster",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			conf, err := ctx.ConfigManager().Find(args[0], false)
			if err != nil {
				return err
			}
			conf.Set("cluster.name", args[1])
			err = conf.Persist()
			if err != nil {
				return err
			}
			ctx.Logger().Infof("Renamed %s to %s", args[0], args[1])
			return nil
		},
	}
	return cmd
}
