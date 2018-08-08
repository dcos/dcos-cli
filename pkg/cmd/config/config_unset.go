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
			conf, err := ctx.ConfigManager().Current()
			if err != nil {
				return err
			}

			conf.Unset(args[0])
			return conf.Persist()
		},
	}
}
