package cmd

import (
	"io"

	"github.com/spf13/cobra"
)

// newCmdConfigUnset creates the `dcos config unset` subcommand.
func newCmdConfigUnset(out, err io.Writer) *cobra.Command {
	return &cobra.Command{
		Use:  "unset",
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			store := attachedCluster().Config.Store()
			store.Unset(args[0])
			return store.Persist()
		},
	}
}
