package cmd

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdConfigShow creates the `dcos config show` subcommand.
func newCmdConfigShow(ctx *cli.Context) *cobra.Command {
	return &cobra.Command{
		Use:  "show",
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			conf, err := ctx.ConfigManager().Current()
			if err != nil {
				return err
			}

			// Show a given config key from the store.
			if len(args) == 1 {
				key := args[0]
				if val := conf.Get(key); val != nil {
					fmt.Printf("%v\n", val)
					return nil
				}
				return fmt.Errorf("unknown key \"%s\"", key)
			}

			// Show all config keys present in the store.
			for _, key := range conf.Keys() {
				if val := conf.Get(key); val != nil {

					// The ACS token should be masked when printing the whole config as it is sensitive data.
					if key == "core.dcos_acs_token" {
						val = "********"
					}
					fmt.Fprintf(ctx.Out(), "%s %v\n", key, val)
				}
			}
			return nil
		},
	}
}
