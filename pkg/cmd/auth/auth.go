package auth

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// NewCommand creates the `dcos auth` subcommand.
func NewCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "auth",
		Short: "Authenticate to DC/OS cluster",
	}
	cmd.AddCommand(
		newCmdAuthListProviders(ctx),
		newCmdAuthLogin(ctx),
		newCmdAuthLogout(ctx),
	)
	return cmd
}
