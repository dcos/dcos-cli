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
		Use:   "attach <cluster>",
		Short: "Attach the CLI to a cluster",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			manager := ctx.ConfigManager()

			// We try to find a Config matching the argument given.
			matchingConf, err := manager.Find(args[0], false)
			if err == config.ErrTooManyConfigs {
				return err
			}

			attachTo := func(conf *config.Config) error {
				err := manager.Attach(conf)
				if err == nil {
					ctx.Logger().Infof("You are now attached to cluster %s", config.NewCluster(conf).ID())
				}
				return err
			}

			currentCluster, err := ctx.Cluster()
			if err != nil {
				if err == config.ErrConfigNotFound {
					return attachTo(matchingConf)
				}
				return err
			}

			clusterLinker := linker.New(ctx.HTTPClient(currentCluster), ctx.Logger())
			linkedClusters, err := clusterLinker.Links()
			if err != nil {
				ctx.Logger().Info(err)
			}

			// We try to find a Link matching the argument given.
			ctx.Logger().Info("Looking for linked cluster...")
			matchingLinkedClusters := linkedClusters[:0]
			for _, linkedCluster := range linkedClusters {
				if args[0] == linkedCluster.Name || strings.HasPrefix(linkedCluster.ID, args[0]) {
					matchingLinkedClusters = append(matchingLinkedClusters, linkedCluster)
				}
			}

			// We act depending on the clusters we have found.
			switch len(matchingLinkedClusters) {
			case 0:
				// No matching linked cluster, one matching cluster.
				if matchingConf != nil {
					return attachTo(matchingConf)
				}
				// No matching linked cluster, no matching cluster.
				return config.ErrConfigNotFound
			case 1:
				// One matching linked cluster, one matching cluster.
				if matchingConf != nil {
					return config.ErrTooManyConfigs
				}
				// One matching linked cluster, no matching cluster.
				flags := setup.NewFlags(ctx.Fs(), ctx.EnvLookup, ctx.Logger())
				flags.LoginFlags().SetProviderID(matchingLinkedClusters[0].LoginProvider.ID)
				_, err := ctx.Setup(flags, matchingLinkedClusters[0].URL, true)
				return err
			default:
				return config.ErrTooManyConfigs
			}
		},
	}
	return cmd
}
