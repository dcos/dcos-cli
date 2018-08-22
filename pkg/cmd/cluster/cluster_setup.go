package cluster

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/setup"

	"github.com/spf13/cobra"
)

// newCmdClusterSetup configures the CLI with a given DC/OS cluster.
func newCmdClusterSetup(ctx api.Context) *cobra.Command {
	setupFlags := setup.NewFlags(ctx.Fs(), ctx.EnvLookup)
	cmd := &cobra.Command{
		Use:   "setup <url>",
		Short: "Set up the CLI to communicate with a cluster",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			clusterURL := args[0]
			ctx.Logger().Info("Setting up the cluster...")
			_, err := ctx.Setup(setupFlags, clusterURL, true)
			if err != nil {
				return err
			}
			ctx.Logger().Info("Your cluster is now setup")
			return err
		},
	}
	setupFlags.Register(cmd.Flags())
	return cmd
}
