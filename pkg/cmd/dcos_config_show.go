package cmd

import (
	"fmt"
	"io"

	"github.com/spf13/cobra"
)

// newCmdConfigShow creates the `dcos config show` subcommand.
func newCmdConfigShow(out, err io.Writer) *cobra.Command {
	return &cobra.Command{
		Use:  "show",
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			store := attachedCluster().Config.Store()

			// Show a given config key from the store.
			if len(args) == 1 {
				key := args[0]
				if val := store.Get(key); val != nil {
					fmt.Printf("%v\n", val)
					return nil
				}
				return fmt.Errorf("unknown key \"%s\"", key)
			}

			// Show all config keys present in the store.
			for _, key := range store.Keys() {
				if val := store.Get(key); val != nil {

					// The ACS token should be masked when printing the whole config as it is sensitive data.
					if key == "core.dcos_acs_token" {
						val = "********"
					}
					fmt.Printf("%s %v\n", key, val)
				}
			}
			return nil
		},
	}
}
