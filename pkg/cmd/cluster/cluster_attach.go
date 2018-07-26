package cluster

import (
	"strings"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cluster/linker"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/setup"
	"github.com/spf13/cobra"
)

// newCmdClusterAttach ataches the CLI to a cluster.
func newCmdClusterAttach(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "attach",
		Short: "Attach the CLI to a cluster",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			manager := ctx.ConfigManager()

			// We try to find a Config matching the argument given.
			matchingConf, err := manager.Find(args[0], false)
			if err == config.ErrTooManyConfigs {
				return err
			}

			// Get the link clusters.
			currentCluster, err := ctx.Cluster()
			if err != nil {
				return err
			}
			clusterLinker := linker.New(ctx.HTTPClient(currentCluster), ctx.Logger())
			linkedClusters, err := clusterLinker.Links()
			if err != nil {
				ctx.Logger().Info(err)
			}

			// We try to find a Link matching the argument given.
			var matchingLinkedClusters []*linker.Link
			for _, linkedCluster := range linkedClusters {
				if args[0] == linkedCluster.Name {
					matchingLinkedClusters = append(matchingLinkedClusters, linkedCluster)
				}
				if args[0] == linkedCluster.ID {
					matchingLinkedClusters = append(matchingLinkedClusters, linkedCluster)
				}
				if strings.HasPrefix(linkedCluster.ID, args[0]) {
					matchingLinkedClusters = append(matchingLinkedClusters, linkedCluster)
				}
			}

			// We act depending on the clusters we have found.
			switch len(matchingLinkedClusters) {
			case 0:
				// No matching linked cluster, one matching cluster.
				if matchingConf != nil {
					return manager.Attach(matchingConf)
				}
				// No matching linked cluster, no matching cluster.
				return config.ErrConfigNotFound
			case 1:
				// One matching linked cluster, one matching cluster.
				if matchingConf != nil {
					return config.ErrTooManyConfigs
				}
				// One matching linked cluster, no matching cluster.
				flags := setup.NewFlags(ctx.Fs(), ctx.EnvLookup)
				flags.LoginFlags().SetProviderID(matchingLinkedClusters[0].LoginProvider.ID)
				cluster, err := ctx.Setup(flags, matchingLinkedClusters[0].URL)
				if err != nil {
					return err
				}
				return ctx.ConfigManager().Attach(cluster.Config())
			default:
				return config.ErrTooManyConfigs
			}
		},
	}
	return cmd
}
