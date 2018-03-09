package cmd

import (
	"github.com/spf13/cobra"
)

// configUnsetCmd represents the `dcos config unset` subcommand.
var configUnsetCmd = &cobra.Command{
	Use:  "unset",
	Args: cobra.ExactArgs(1),
	RunE: runConfigUnsetCmd,
}

func runConfigUnsetCmd(cmd *cobra.Command, args []string) error {
	store := attachedCluster().Config.Store()
	store.Unset(args[0])
	return store.Save()
}

func init() {
	configCmd.AddCommand(configUnsetCmd)
}
