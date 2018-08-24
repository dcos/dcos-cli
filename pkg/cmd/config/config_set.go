package config

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/spf13/cobra"
)

// newCmdConfigSet creates the `dcos config set` subcommand.
func newCmdConfigSet(ctx api.Context) *cobra.Command {
	return &cobra.Command{
		Use:   "set <name> <value>",
		Short: "Add or set a property in the configuration file used for the current cluster",
		Long:  "The properties that can be set are: core.dcos_url, core.dcos_acs_token, core.ssl_verify, core.timeout, core.ssh_user, core_ssh_proxy_ip, core.pagination, core.reporting, core.mesos_master_url, core_prompt_login",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			cluster, err := ctx.Cluster()
			if err != nil {
				return err
			}
			conf := cluster.Config()
			conf.Set(args[0], args[1])
			err = conf.Persist()
			if err != nil {
				return err
			}
			ctx.Logger().Infof("Config value %s was set to %s", args[0], args[1])
			return nil
		},
	}
}
