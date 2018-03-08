package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

// clusterCmd represents the `dcos cluster` subcommand.
var clusterCmd = &cobra.Command{
	Use: "cluster",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("cluster called")
	},
}

func init() {
	rootCmd.AddCommand(clusterCmd)
}
