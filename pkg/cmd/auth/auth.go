package auth

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// NewCommand creates the `dcos auth` subcommand.
func NewCommand(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "auth",
	}
	cmd.AddCommand(
		newCmdAuthListProviders(ctx),
	)
	return cmd
}
