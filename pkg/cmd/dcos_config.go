package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdConfig creates the `dcos config` subcommand.
func newCmdConfig(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "config",
	}
	cmd.AddCommand(
		newCmdConfigSet(ctx),
		newCmdConfigShow(ctx),
		newCmdConfigUnset(ctx),
	)
	return cmd
}
