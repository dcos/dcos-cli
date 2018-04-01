package cmd

import (
	"io"

	"github.com/spf13/cobra"
)

// newCmdConfigSet creates the `dcos config set` subcommand.
func newCmdConfigSet(out, err io.Writer) *cobra.Command {
	return &cobra.Command{
		Use:  "set",
		Args: cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			store := attachedCluster().Config.Store()
			store.Set(args[0], args[1])
			return store.Persist()
		},
	}
}
