package cmd

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/spf13/cobra"
)

// configShowCmd represents the `dcos config show` subcommand.
var configShowCmd = &cobra.Command{
	Use:  "show",
	Args: cobra.MaximumNArgs(1),
	RunE: runConfigShowCmd,
}

var maskedKeys = []string{
	"core.dcos_acs_token",
}

func runConfigShowCmd(cmd *cobra.Command, args []string) error {
	store := attachedCluster().Config.Store()

	if len(args) == 1 {
		return configShow(store, args[0])
	}

	configShowAll(store)
	return nil
}

func configShowAll(store *config.Store) {
	for _, key := range store.Keys() {
		if val := store.Get(key); val != nil {
			for _, maskedKey := range maskedKeys {
				if maskedKey == key {
					val = "********"
					break
				}
			}
			fmt.Printf("%s %v\n", key, val)
		}
	}
}

func configShow(store *config.Store, key string) error {
	if val := store.Get(key); val != nil {
		fmt.Printf("%v\n", val)
		return nil
	}
	return fmt.Errorf("unknown key \"%s\"", key)
}

func init() {
	configCmd.AddCommand(configShowCmd)
}
