package cluster

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/spf13/cobra"
)

// newCmdClusterOpen opens the current cluster UI in the user browser.
func newCmdClusterOpen(ctx api.Context) *cobra.Command {

	cmd := &cobra.Command{
		Use:   "open [<cluster>]",
		Short: "Open a cluster UI in the browser",
		Example: `
  # Open the current cluster UI in the browser
  dcos cluster open

  # Open a specific cluster UI in the browser (using a name or ID of a configured cluster)
  dcos cluster open my-cluster-1`,
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var cluster *config.Cluster

			if len(args) == 1 {
				manager, err := ctx.ConfigManager()
				if err != nil {
					return err
				}
				conf, err := manager.Find(args[0], false)
				if err != nil {
					return err
				}
				cluster = config.NewCluster(conf)
			} else {
				var err error
				cluster, err = ctx.Cluster()
				if err != nil {
					return err
				}
			}

			return ctx.Opener().Open(cluster.URL())
		},
	}
	return cmd
}
