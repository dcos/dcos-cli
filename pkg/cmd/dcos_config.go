package cmd

import (
	"io"

	"github.com/spf13/cobra"
)

// newCmdConfig creates the `dcos config` subcommand.
func newCmdConfig(out, err io.Writer) *cobra.Command {
	cmd := &cobra.Command{
		Use: "config",
	}
	cmd.AddCommand(
		newCmdConfigSet(out, err),
		newCmdConfigShow(out, err),
		newCmdConfigUnset(out, err),
	)
	return cmd
}
