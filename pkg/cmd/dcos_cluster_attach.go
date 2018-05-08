package cmd

import (
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func newSubCmdClusterAttach(ctx *cli.Context) subcommand.SubCommand {
	sc := subcommand.NewInternalSubCommand(newCmdClusterAttach(ctx))
	sc.Autocomplete = cmdClusterAttachAutocomplete

	return sc
}

func cmdClusterAttachAutocomplete(cmd *cobra.Command, args []string, ctx *cli.Context) []string {
	// return the names of the clusters known to this cli
	var out []string
	for _, c := range ctx.Clusters() {
		out = append(out, c.Name())
	}
	return out
}

// newCmdClusterAttach ataches the CLI to a cluster.
func newCmdClusterAttach(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "attach",
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			manager := ctx.ConfigManager()
			conf, err := manager.Find(args[0], false)
			if err != nil {
				return err
			}
			return manager.Attach(conf)
		},
	}
	return cmd
}
