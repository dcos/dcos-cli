package subcommand

import (
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
	CommandName string
	subcommands []SubCommand
	RunCmd      func(ctx *cli.Context) *cobra.Command
	AutoCmd     func(cmd *cobra.Command, args []string, ctx *cli.Context) []string
}

// AddSubCommand adds the given subcommand(s). These will be added to RunCmd and AutocompleteCmd as children
// of the cobra Command on creation.
func (i *InternalCommand) AddSubCommand(commands ...SubCommand) {
	i.subcommands = append(i.subcommands, commands...)
}

// Name returns the Command's name used by cobra when searching for dispatch.
func (i *InternalCommand) Name() string {
	return i.CommandName
}

// RunCommand builds and returns the cobra.Command to run for this subcommand.
func (i *InternalCommand) RunCommand(ctx *cli.Context) *cobra.Command {
	cmd := i.RunCmd(ctx)
	for _, sc := range i.subcommands {
		cmd.AddCommand(sc.RunCommand(ctx))
	}
	return cmd
}

// AutocompleteCommand builds and returns the cobra.Command to run when getting autocomplete options.
func (i *InternalCommand) AutocompleteCommand(ctx *cli.Context) *cobra.Command {
	/*
		cmd := i.AutoCmd(ctx)
		for _, sc := range i.subcommands {
			cmd.AddCommand(sc.AutocompleteCommand(ctx))
		}
		return cmd
	*/
	runCmd := i.RunCmd(ctx).Flags()
	cmd := &cobra.Command{
		Use: i.Name(),
		RunE: func(cmd *cobra.Command, args []string) error {
			if i.AutoCmd != nil {
				i.AutoCmd(cmd, args, ctx)
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
