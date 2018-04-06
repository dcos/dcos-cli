package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdAuth creates the `dcos auth` subcommand.
func newCmdAuth(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "auth",
	}
	cmd.AddCommand(
		newCmdAuthListProviders(ctx),
	)
	return cmd
}
