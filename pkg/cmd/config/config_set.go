package config

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdConfigSet creates the `dcos config set` subcommand.
func newCmdConfigSet(ctx *cli.Context) *cobra.Command {
	return &cobra.Command{
		Use:  "set",
		Args: cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			conf, err := ctx.ConfigManager().Current()
			if err != nil {
				return err
			}

			conf.Set(args[0], args[1])
			return conf.Persist()
		},
	}
}
