package cmd

import (
	"github.com/spf13/cobra"
)

// configCmd represents the `dcos config` subcommand.
var configCmd = &cobra.Command{
	Use: "config",
}

func init() {
	rootCmd.AddCommand(configCmd)
}
