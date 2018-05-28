package auth

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func NewDcosCmdAuth(ctx *cli.Context) subcommand.DcosCommand {
	sc := subcommand.NewInternalCommand(NewCommand(ctx))

	sc.AddSubCommand(
		newDcosCmdAuthListProviders(ctx),
	)
	return sc
}

// NewCommand creates the `dcos auth` subcommand.
func NewCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "auth",
	}
	cmd.AddCommand(
		newCmdAuthListProviders(ctx),
		newCmdAuthLogin(ctx),
	)
	return cmd
}
