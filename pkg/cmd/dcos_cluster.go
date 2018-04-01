package cmd

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdCluster creates the `dcos cluster` subcommand.
func newCmdCluster(ctx *cli.Context) *cobra.Command {
	return &cobra.Command{
		Use: "cluster",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Println("cluster called")
		},
	}
}
