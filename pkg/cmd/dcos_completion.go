package cmd

import (
	"errors"
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

const (
	bashCompletion = `
__dcos_debug()
{
	if [[ -n ${DCOS_COMP_DEBUG_FILE} ]]; then
		echo "$*" >> "${DCOS_COMP_DEBUG_FILE}"
	fi
}

_dcos()
{
	local cur prev
	cur=${COMP_WORDS[COMP_CWORD]}

	local dcos_out
	# The use of [@]:1 is to chop off the leading 'dcos' which cobra won't get rid of otherwise but does
	# for commands run normally
	if dcos_out=$(dcos __autocomplete__ ${COMP_WORDS[@]:1} 2>/dev/null); then
		__dcos_debug ${dcos_out}
		COMPREPLY=( $(compgen -W "${dcos_out[*]}" -- "$cur") )
	fi
}

complete -o default -F _dcos dcos
`
)

func newSubCmdCompletion(ctx *cli.Context) subcommand.SubCommand {
	sc := subcommand.NewInternalSubCommand(newCmdCompletion(ctx))
	return sc
}

func newCmdCompletion(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:       "completion",
		ValidArgs: []string{"bash", "zsh"},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return errors.New("no shell given")
			}
			switch args[0] {
			case "bash":
				fmt.Fprint(ctx.Out(), bashCompletion)
			case "zsh":
				fmt.Fprint(ctx.Out(), bashCompletion)
			default:
				return fmt.Errorf("invalid shell %s given", args[0])
			}
			return nil
		},
	}

	return cmd
}
