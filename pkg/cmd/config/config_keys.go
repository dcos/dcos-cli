package config

import (
	"fmt"
	"sort"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/spf13/cobra"
)

// newCmdConfigKeys returns the keys that a user can set in a configuration file.
func newCmdConfigKeys(ctx api.Context) *cobra.Command {
	var quietOutput bool
	cmd := &cobra.Command{
		Use:   "keys",
		Short: "Print all the keys that can be set in a configuration file",
		Args:  cobra.NoArgs,
		Run: func(cmd *cobra.Command, args []string) {
			configKeys := config.Keys()
			var sortedKeys []string
			for k := range configKeys {
				sortedKeys = append(sortedKeys, k)
			}
			sort.Strings(sortedKeys)
			for _, key := range sortedKeys {
				if quietOutput {
					fmt.Fprintln(ctx.Out(), key)
				} else {
					fmt.Fprintln(ctx.Out(), key+" : "+configKeys[key])
				}

			}
		},
	}
	cmd.Flags().BoolVarP(&quietOutput, "quiet", "q", false, "Only print config keys")
	return cmd
}
