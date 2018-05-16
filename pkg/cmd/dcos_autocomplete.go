package cmd

import (
	"errors"
	"fmt"
	"strings"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
	flag "github.com/spf13/pflag"
)

func newAutocompleteCommand(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "__autocomplete__",

		// Hide it from the Usage output
		Hidden: true,

		// This needs to be true to prevent __autocomplete__ from trying to parse flags that are meant for
		// the commands it's trying to complete and causing completion to fail because it takes no flags
		// itself so any flags will break it.
		DisableFlagParsing: true,
		Args:               cobra.MinimumNArgs(1),
		ValidArgs:          []string{"bash", "zsh"},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return errors.New("no arguments given")
			}
			shell := args[0]

			// root.Find will error out if it's given a flag that isn't accepted by the command it finds so
			// we need to strip out the flags currently in the list to give just the command names to
			// Find.
			commands, flags := stripFlags(args[1:])
			flagComplete := isFlag(args[len(args)-1])
			root := cmd.Parent()

			var completions []string

			switch shell {
			case "zsh":
			case "bash":
				command, _, err := root.Find(commands)
				if err != nil {
					// if no command was found, default to the root
					command = root
				}

				// We'll need to determine whether or not the found command is internal or external here.
				// To do that we use the Annotations object which the cobra documentation doesn't say much
				// about but appears to be for arbitrary metadata so we can use that to hold whether or
				// not a command is internal or external. In this case we're only interested in whether the
				// external key exists because we assume the default is internal.
				if _, exists := cmd.Annotations["external"]; exists {
					completions = externalCompletion(command)
				} else {
					completions = internalCompletion(command, flags, flagComplete)
				}

				completions = append(completions, customCompletion(command, ctx)...)
			default:
				return fmt.Errorf("no completion implemented for shell %s", shell)
			}

			for _, c := range completions {
				fmt.Fprintln(ctx.Out(), c)
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
			if !c.Hidden {
				out = append(out, c.Name())
			}
		}
		out = append(out, cmd.ValidArgs...)
	} else {
		flagSet := cmd.Flags()
		flagSet.VisitAll(func(f *flag.Flag) {
			if f.Name != "" {
				name := "--" + f.Name
				out = append(out, name)
			}
			if f.Shorthand != "" {
				shorthand := "-" + f.Shorthand
				out = append(out, shorthand)
			}
		})
	}
	return out
}

func externalCompletion(cmd *cobra.Command) []string {
	return []string{}
}

func customCompletion(cmd *cobra.Command, ctx *cli.Context) []string {
	funcName, exists := cmd.Annotations["custom_completion"]
	if !exists {
		// custom_completion is optional so bail out now.
		return []string{}
	}

	out := []string{}

	switch funcName {
	case "cluster_list":
		for _, c := range ctx.Clusters() {
			out = append(out, c.Name())
		}
	default:
	}

	return out
}
