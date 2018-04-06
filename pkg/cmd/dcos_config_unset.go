package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdConfigUnset creates the `dcos config unset` subcommand.
func newCmdConfigUnset(ctx *cli.Context) *cobra.Command {
	return &cobra.Command{
		Use:  "unset",
		Args: cobra.ExactArgs(1),
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
