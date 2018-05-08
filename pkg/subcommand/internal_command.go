package subcommand

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// InternalCommand is for commands that exist in the current binary.
type InternalCommand struct {
	Command     *cobra.Command
	subcommands []SubCommand

	// Autocomplete isn't a cobra command because we want some default behavior like automatically
	// completing subcommands or arguments of the associated Command so this function is embedded within
	// the actual cobra Command in InternalCommand's AutocompleteCommand function
	// cmd is this.Command, not the cobra.Command running the autocomplete function as it normally is
	Autocomplete func(cmd *cobra.Command, args []string, ctx *cli.Context) []string
}

// NewInternalSubCommand takes in a cobra command struct and creates a wrapping SubCommand from it.
// It's counterintuitive but this function does NOT automatically add all of the children of the given
// cmd as subcommands here. This is because we need to allow the children to assign an autocomplete
// function which means knowing what function to call for each of the children to allow them to put
// together a subcommand however they see fit. The subcommands are added as children of the cobra
// command in RunCommand.
// This also means that children should not be added to the wrapped cobra.Command directly. If they are
// the commands will be present twice in the list.
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
func (i *InternalCommand) RunCommand() *cobra.Command {
	cmd := i.Command
	for _, sc := range i.subcommands {
		cmd.AddCommand(sc.RunCommand())
	}
	return i.Command
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

			if i.Autocomplete != nil {
				out = append(out, i.Autocomplete(i.Command, args, ctx)...)
			}

			// Pull from RunCommand's args, not the autocomplete command's
			if len(i.Command.ValidArgs) > 0 {
				for _, arg := range i.Command.ValidArgs {
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
