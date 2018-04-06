// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// NewDCOSCommand creates the `dcos` command with its `auth`, `config`, and `cluster` subcommands.
func NewDCOSCommand(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "dcos",
	}
	cmd.AddCommand(
		newCmdAuth(ctx),
		newCmdConfig(ctx),
		newCmdCluster(ctx),
	)
	return cmd
}
