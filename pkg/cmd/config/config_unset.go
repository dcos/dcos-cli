package config

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdConfigUnset creates the `dcos config unset` subcommand.
func newCmdConfigUnset(ctx api.Context) *cobra.Command {
	return &cobra.Command{
		Use:   "unset <name>",
		Short: "Remove a property from the configuration file used for the current cluster",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cluster, err := ctx.Cluster()
			if err != nil {
				return err
			}
			conf := cluster.Config()
			conf.Unset(args[0])
			err = conf.Persist()
			if err != nil {
				return err
			}
			ctx.Logger().Infof("Config value %s was removed", args[0])
			return nil
		},
	}
}
