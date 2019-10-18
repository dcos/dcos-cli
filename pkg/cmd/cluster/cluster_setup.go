package cluster

import (
	"errors"
	"fmt"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/setup"

	"github.com/spf13/cobra"
)

// newCmdClusterSetup configures the CLI with a given DC/OS cluster.
func newCmdClusterSetup(ctx api.Context) *cobra.Command {
	setupFlags := setup.NewFlags(ctx.Fs(), ctx.EnvLookup, ctx.Logger())
	cmd := &cobra.Command{
		Use:   "setup <url>",
		Short: "Set up the CLI to communicate with a cluster",
		Args: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return errors.New("missing cluster URL")
			}
			if len(args) > 1 {
				return fmt.Errorf("received %d arguments %s, expects a single cluster URL", len(args), args)
			}
			return nil
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			clusterURL := args[0]
			_, err := ctx.Setup(setupFlags, clusterURL, true)
			return err
		},
	}
	setupFlags.Register(cmd.Flags())
	return cmd
}
