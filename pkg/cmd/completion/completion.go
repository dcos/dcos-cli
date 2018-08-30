package completion

//go:generate go-bindata -pkg completion -o completion_data.gen.go -nometadata completion.sh

import (
	"fmt"

	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// NewCommand creates the `dcos completion` subcommand
func NewCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:       "completion",
		Short:     "Output completion script for the DC/OS CLI",
		Hidden:    true,
		ValidArgs: []string{"bash"},
		Args:      cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			shell := args[0]
			switch shell {
			case "bash":
				return genBashCompletion(ctx)
			default:
				return fmt.Errorf("invalid shell '%s' given", shell)
			}
		},
	}

	return cmd
}

func genBashCompletion(ctx api.Context) error {
	data, err := Asset("completion.sh")
	if err != nil {
		return err
	}

	fmt.Fprint(ctx.Out(), string(data))
	return nil
}
