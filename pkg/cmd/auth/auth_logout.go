package auth

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdAuthLogout creates the `dcos auth logout` subcommand.
// This unset the key `core.dcos_acs_token` in the current config.
func newCmdAuthLogout(ctx api.Context) *cobra.Command {
	return &cobra.Command{
		Use:  "logout",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			conf, err := ctx.ConfigManager().Current()
			if err != nil {
				return err
			}

			conf.Unset("core.dcos_acs_token")
			return conf.Persist()
		},
	}
}

