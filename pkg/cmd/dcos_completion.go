package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

const (
	bashCompletion = `

`
)

func newSubCmdCompletion(ctx *cli.Context) subcommand.SubCommand {
	sc := subcommand.NewInternalSubCommand(newCmdCompletion(ctx))
	return sc
}

func newCmdCompletion(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:       "completion",
		ValidArgs: []string{"bash", "zsh"},
		RunE: func(cmd *cobra.Command, args []string) error {
			return nil
		},
	}

	return cmd
}
