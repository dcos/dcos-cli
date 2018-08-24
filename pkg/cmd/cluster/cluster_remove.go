package cluster

import (
	"errors"
	"path/filepath"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cluster/lister"
	"github.com/spf13/cobra"
)

// newCmdClusterRemove removes a cluster.
func newCmdClusterRemove(ctx api.Context) *cobra.Command {
	var removeAll bool
	var removeUnavailable bool

	cmd := &cobra.Command{
		Use:   "remove <cluster>",
		Short: "Remove a configured cluster from the CLI",
		Args:  cobra.MaximumNArgs(1),
		PreRunE: func(cmd *cobra.Command, args []string) error {
			if (removeAll || removeUnavailable) && len(args) == 1 {
				return errors.New("cannot accept both a cluster name and the --all / --unavailable option")
			}
			if !removeAll && !removeUnavailable && len(args) == 0 {
				return errors.New("either a cluster name or one of the --all / --unavailable option must be passed")
			}
			return nil
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			// Remove a single cluster.
			if len(args) == 1 {
				conf, err := ctx.ConfigManager().Find(args[0], false)
				if err != nil {
					return err
				}
				err = ctx.Fs().RemoveAll(filepath.Dir(conf.Path()))
				if err != nil {
					return err
				}

				ctx.Logger().Infof("Removed cluster: %s", args[0])
				return nil
			}

			var filters []lister.Filter
			if removeUnavailable {
				filters = append(filters, lister.Status(lister.StatusUnavailable))
			}

			items := lister.New(ctx.ConfigManager(), ctx.Logger()).List(filters...)

			for _, item := range items {
				if err := ctx.Fs().RemoveAll(item.Cluster().Dir()); err != nil {
					return err
				}
				ctx.Logger().Infof("Removed cluster %s ...", item.ID)
			}
			return nil
		},
	}
	cmd.Flags().BoolVar(&removeAll, "all", false, "remove all clusters")
	cmd.Flags().BoolVar(&removeUnavailable, "unavailable", false, "remove unavailable clusters")
	return cmd
}
