package cmd

import (
	"fmt"
	"io"

	"github.com/spf13/cobra"
)

// newCmdCluster creates the `dcos cluster` subcommand.
func newCmdCluster(out, err io.Writer) *cobra.Command {
	return &cobra.Command{
		Use: "cluster",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Println("cluster called")
		},
	}
}
