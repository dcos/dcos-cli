package cluster

import (
	"errors"
	"path/filepath"

	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdClusterRemove removes a cluster.
func newCmdClusterRemove(ctx api.Context) *cobra.Command {
	var removeAll bool
	cmd := &cobra.Command{
		Use:   "remove <cluster>",
		Short: "Remove a configured cluster from the CLI",
		Args:  cobra.MaximumNArgs(1),
		PreRunE: func(cmd *cobra.Command, args []string) error {
			if removeAll && len(args) == 1 {
				return errors.New("cannot accept both a cluster name and the --all option")
			}
			if !removeAll && len(args) == 0 {
				return errors.New("either a cluster name or the --all option must be passed")
			}
			return nil
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			// Remove all clusters.
			if removeAll {
				for _, conf := range ctx.ConfigManager().All() {
					if err := ctx.Fs().RemoveAll(filepath.Dir(conf.Path())); err != nil {
						return err
					}
				}
				return nil
			}

			// Remove a single cluster.
			conf, err := ctx.ConfigManager().Find(args[0], false)
			if err != nil {
				return err
			}
			return ctx.Fs().RemoveAll(filepath.Dir(conf.Path()))
		},
	}
	cmd.Flags().BoolVar(&removeAll, "all", false, "remove all clusters")
	return cmd
}
