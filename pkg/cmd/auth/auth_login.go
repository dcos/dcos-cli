package auth

import (
	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/spf13/cobra"
)

// newCmdAuthLogin creates the `dcos auth login` subcommand.
func newCmdAuthLogin(ctx api.Context) *cobra.Command {
	flags := login.NewFlags(ctx.Fs(), ctx.EnvLookup, ctx.Logger())
	cmd := &cobra.Command{
		Use:   "login",
		Short: "Log in to the current cluster",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			cluster, err := ctx.Cluster()
			if err != nil {
				return err
			}
			acsToken, err := ctx.Login(flags, ctx.HTTPClient(cluster))
			if err != nil {
				return err
			}
			cluster.SetACSToken(acsToken)
			err = cluster.Config().Persist()
			if err != nil {
				return err
			}
			ctx.Logger().Info("Login successful")
			return nil
		},
	}
	flags.Register(cmd.Flags())
	return cmd
}
