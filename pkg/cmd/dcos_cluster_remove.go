package cmd

import (
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdClusterRemove removes a cluster.
func newCmdClusterRemove(ctx *cli.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "remove",
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			conf, err := ctx.ConfigManager().Find(args[0], false)
			if err != nil {
				return err
			}
			return ctx.Fs.RemoveAll(filepath.Dir(conf.Path()))
		},
	}
	return cmd
}
