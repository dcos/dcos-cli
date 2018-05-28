package subcommand

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// DcosCommand defines a subcommand interface that provides the correct cobra command at runtime.
type DcosCommand interface {
	// RunCommand returns the cobra command that will be used when this subcommand is supposed to be run.
	RunCommand() *cobra.Command
	// Autocomplete returns the cobra command that will be used when this command is being autocompleted.
	AutocompleteCommand(ctx *cli.Context) *cobra.Command
	// Name returns the name of the cobra Command from RunCommand().Use.
	Name() string
}
