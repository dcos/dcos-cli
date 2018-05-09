package subcommand

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// InternalCommand is for commands that exist in the current binary.
type InternalCommand struct {
	// command is the cobra.command that will be used when the command is run. It's stored here as a command
	// instead of, for example, a function, because we want to allow the definition of args, flags, and other
	// cobra options without replicating the API here. This also means we have an easier time inspecting the
	// command to be run while doing autocompletion because the actual command will always exist alongside
	// the autocomplete function.
	command     *cobra.Command
	subcommands []SubCommand

	// autocomplete isn't a cobra command because we want some default behavior like automatically
	// completing subcommands or arguments of the associated Command so this function is embedded within
	// the actual cobra Command in InternalCommand's AutocompleteCommand function
	// cmd is this.Command, not the cobra.Command running the autocomplete function as it normally is
	autocomplete func(cmd *cobra.Command, args []string, ctx *cli.Context) []string
}

// NewInternalCommand takes in a cobra command struct and creates a wrapping SubCommand from it.
// It's counterintuitive but this function does NOT automatically add all of the children of the given
// cmd as subcommands here. This is because we need to allow the children to assign an autocomplete
// function which means knowing what function to call for each of the children to allow them to put
// together a subcommand however they see fit. The subcommands are added as children of the cobra
// command in RunCommand.
// This also means that children should not be added to the wrapped cobra.Command directly. If they are
// the commands will be present twice in the list.
func NewInternalCommand(cmd *cobra.Command) *InternalCommand {
	i := &InternalCommand{
		command: cmd,
	}
	return i
}

// AddAutocomplete adds a custom autocomplete function to the InternalCommand
func (i *InternalCommand) AddAutocomplete(a func(cmd *cobra.Command, args []string, ctx *cli.Context) []string) {
	i.autocomplete = a
}

// AddSubCommand adds the given subcommand(s). These will be added to RunCmd and AutocompleteCmd as children
// of the cobra Command on creation.
func (i *InternalCommand) AddSubCommand(commands ...SubCommand) {
	i.subcommands = append(i.subcommands, commands...)
}

// Name returns the Command's name used by cobra when searching for dispatch.
func (i *InternalCommand) Name() string {
	return i.command.Use
}

// RunCommand builds and returns the cobra.Command to run for this subcommand.
func (i *InternalCommand) RunCommand() *cobra.Command {
	cmd := i.command
	for _, sc := range i.subcommands {
		cmd.AddCommand(sc.RunCommand())
	}
	return i.command
}

// AutocompleteCommand builds and returns the cobra.Command to run when getting autocomplete options.
func (i *InternalCommand) AutocompleteCommand(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: i.Name(),
		// This allows commands to capture incomplete input of the next command e.g. `dcos a` will fail to
		// match any command without allowing for the autocomplete command to take args
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			// simple case is to return the subcommand names under this current function
			var out []string
			for _, sc := range i.subcommands {
				out = append(out, sc.Name())
			}

			if i.autocomplete != nil {
				out = append(out, i.autocomplete(i.command, args, ctx)...)
			}

			// Pull from RunCommand's args, not the autocomplete command's
			if len(i.command.ValidArgs) > 0 {
				for _, arg := range i.command.ValidArgs {
					out = append(out, arg)
				}
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
