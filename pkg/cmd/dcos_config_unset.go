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
	conf := attachedCluster().Config
	conf.Store().Unset(args[0])
	return conf.Save()
}

func init() {
	configCmd.AddCommand(configUnsetCmd)
}
