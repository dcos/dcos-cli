package plugin

import (
	"fmt"
	"strings"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/spf13/cobra"
)

// newCmdPluginAdd creates the `dcos plugin add` subcommand.
func newCmdPluginAdd(ctx api.Context) *cobra.Command {
	installOpts := &plugin.InstallOpts{}
	cmd := &cobra.Command{
		Use:   "add <resource>",
		Short: "Add a CLI plugin",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cluster, err := ctx.Cluster()
			if err != nil {
				return err
			}

			p, err := ctx.PluginManager(cluster).Install(args[0], installOpts)
			if err != nil {
				return err
			}

			fmt.Fprintf(ctx.ErrOut(), "New commands available: %s\n", strings.Join(p.CommandNames(), ", "))
			return nil
		},
	}
	cmd.Flags().BoolVarP(&installOpts.Update, "update", "u", false, "")
	return cmd
}
