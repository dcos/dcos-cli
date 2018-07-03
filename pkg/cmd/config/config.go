package config

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// NewCommand creates the `dcos config` subcommand.
func NewCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "config",
		Short: "Manage the DC/OS configuration file",
	}
	cmd.AddCommand(
		newCmdConfigSet(ctx),
		newCmdConfigShow(ctx),
		newCmdConfigUnset(ctx),
	)
	return cmd
}
