package cluster

import (
	"errors"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/spf13/cobra"
)

// newCmdClusterLink links the attached cluster to another one.
func newCmdClusterUnlink(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "unlink",
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			attachedCluster, err := ctx.Cluster()
			if err != nil {
				return err
			}

			var linkedCluster config.Cluster
			for _, cluster := range ctx.Clusters() {
				if args[0] == cluster.ID() ||
					(args[0] == cluster.Name() && ctx.IsUniqueCluster(cluster.Name())) {
					linkedCluster = *cluster
					break
				}
			}

			if (config.Cluster{}) == linkedCluster {
				return errors.New("unable to retrieve cluster " + args[0])
			}

			if attachedCluster.ID() == linkedCluster.ID() {
				return errors.New("cannot unlink a cluster to itself")
			}

			client := ctx.HTTPClient(attachedCluster)
			_, err = client.Delete("/cluster/v1/links/" + linkedCluster.ID())
			if err != nil {
				return err
			}

			return nil
		},
	}
	return cmd
}
