package cmd

import (
	"fmt"
	"io"

	"github.com/spf13/cobra"
)

// newCmdAuth creates the `dcos auth` subcommand.
func newCmdAuth(out, err io.Writer) *cobra.Command {
	return &cobra.Command{
		Use: "auth",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Println("auth called")
		},
	}
}
