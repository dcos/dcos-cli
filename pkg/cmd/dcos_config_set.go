package cmd

import (
	"github.com/spf13/cobra"
)

// configSetCmd represents the `dcos config set` subcommand.
var configSetCmd = &cobra.Command{
	Use:  "set",
	Args: cobra.ExactArgs(2),
	RunE: runConfigSetCmd,
}

func runConfigSetCmd(cmd *cobra.Command, args []string) error {
	store := attachedCluster().Config.Store()
	store.Set(args[0], args[1])
	return store.Save()
}

func init() {
	configCmd.AddCommand(configSetCmd)
}
