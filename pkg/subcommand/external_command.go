package subcommand

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// ExternalCommand represents commands that are available but aren't located in this binary. This will be
// commands like Core CLI-specific commands or package extensions
type ExternalCommand struct {
	CommandName string
	BinaryPath  string
}

// Name returns the Command's name used by cobra when searching for dispatch.
func (e *ExternalCommand) Name() string {
	return e.CommandName
}

// RunCommand builds and returns the cobra.Command to run for this subcommand.
func (e *ExternalCommand) RunCommand(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: e.Name(),
		RunE: func(cmd *cobra.Command, args []string) error {
			// Shell out to external binary
			fmt.Printf("External command %s called with args %s\n", e.Name(), args)
			return nil
		},
	}
	return cmd
}

// AutocompleteCommand builds and returns the cobra.Command to run when getting autocomplete options.
func (e *ExternalCommand) AutocompleteCommand(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: e.Name(),
		RunE: func(cmd *cobra.Command, args []string) error {
			// Shell out to external binary
			fmt.Printf("External autocomplete command %s called with args %s\n", e.Name(), args)
			return nil
		},
	}
	return cmd
}
