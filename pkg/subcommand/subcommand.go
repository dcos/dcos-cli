package subcommand

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// SubCommand defines a subcommand interface that provides the correct cobra command at runtime.
type SubCommand interface {
	RunCommand(ctx *cli.Context) *cobra.Command
	AutocompleteCommand(ctx *cli.Context) *cobra.Command
	Name() string
}

// InternalCommand is for commands that exist in the current binary.
type InternalCommand struct {
	Command      *cobra.Command
	subcommands  []SubCommand
	Autocomplete func(cmd *cobra.Command, args []string, ctx *cli.Context) []string
}

// NewInternalSubCommand takes in a cobra command struct and creates a wrapping SubCommand from it.
func NewInternalSubCommand(cmd *cobra.Command) *InternalCommand {
	i := &InternalCommand{
		Command: cmd,
	}
	return i
}

// AddSubCommand adds the given subcommand(s). These will be added to RunCmd and AutocompleteCmd as children
// of the cobra Command on creation.
func (i *InternalCommand) AddSubCommand(commands ...SubCommand) {
	i.subcommands = append(i.subcommands, commands...)
}

// Name returns the Command's name used by cobra when searching for dispatch.
func (i *InternalCommand) Name() string {
	return i.Command.Use
}

// RunCommand builds and returns the cobra.Command to run for this subcommand.
func (i *InternalCommand) RunCommand(ctx *cli.Context) *cobra.Command {
	cmd := i.Command
	for _, sc := range i.subcommands {
		cmd.AddCommand(sc.RunCommand(ctx))
	}
	return i.Command
}

// AutocompleteCommand builds and returns the cobra.Command to run when getting autocomplete options.
func (i *InternalCommand) AutocompleteCommand(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: i.Name(),
		RunE: func(cmd *cobra.Command, args []string) error {
			// simple case is to return the subcommand names under this current function
			var out []string
			for _, sc := range i.subcommands {
				out = append(out, sc.Name())
			}

			if i.Autocomplete != nil {
				i.Autocomplete(cmd, args, ctx)
			}

			for _, completion := range out {
				fmt.Fprintln(ctx.Out(), completion)
			}
			return nil
		},
	}
	for _, sc := range i.subcommands {
		cmd.AddCommand(sc.AutocompleteCommand(ctx))
	}

	return cmd
}

// ExternalCommand represents commands that are available but aren't located in this binary. This will be
// commands like Core CLI-specific commands or package extensions
type ExternalCommand struct {
	CommandName string
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
			return nil
		},
	}
	return cmd
}
