package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func newSubCmdAuth(ctx *cli.Context) subcommand.SubCommand {
	sc := subcommand.NewInternalSubCommand(newCmdAuth(ctx))

	sc.AddSubCommand(
		newSubCmdAuthListProviders(ctx),
	)
	return sc
}

// newCmdAuth creates the `dcos auth` subcommand.
func newCmdAuth(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "auth",
	}
	return cmd
}
