package cmd

import (
	"errors"
	"strings"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

func newAutocompleteCommand(ctx *cli.Context) *cobra.Command {
	// We can either implement shell specification with an optional flag or we can require it as an
	// argument taken by __autocomplete__. Thinking about it, I think giving it as the first argument
	// is best because we'll only ever support a few shell types and users won't be typing these commands
	// in manually.
	cmd := &cobra.Command{
		Use:  "__autocomplete__",
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return errors.New("no arguments given")
			}
			shell := args[0]
			commands, flags := stripFlags(args[1:])
			flagComplete := isFlag(args[len(args)-1])
			root := cmd.Parent()

			switch shell {
			case "bash":
				// root.Find will return the stuff remaining from after the words that matched the commands
				// (e.g. `cluster att` will give ["att"]).
				// However, if there are incorrect or, unfortunately, incomplete flags, this will error out
				// so if they're completing on a flag with something like `auth list-providers --j`,
				// it'll error
				command, remaining, err := root.Find(commands)
				if err != nil {
					return err
				}

				internalCompletion(command, flags, flagComplete)
			case "zsh":
			default:
			}

			return nil
		},
	}

	return cmd
}

func isFlag(arg string) bool {
	return strings.HasPrefix(arg, "-")
}

func stripFlags(args []string) ([]string, []string) {
	var commands []string
	var flags []string
	for _, a := range args {
		if isFlag(a) {
			flags = append(flags, a)
		} else {
			commands = append(commands, a)
		}
	}
	return commands, flags
}

func internalCompletion(cmd *cobra.Command, flags []string, flagComplete bool) []string {
	var out []string
	if !flagComplete {
		// subcommand or argument completion
		for _, c := range cmd.Commands() {
			out = append(out, c.Name())
		}
		out = append(out, cmd.ValidArgs...)
	} else {
		flagSet := cmd.Flags()
	}
	return out
}

func externalCompletion(cmd *cobra.Command, flag bool) []string {
	return []string{}
}
