package cluster

import (
	"errors"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/clusterlinker"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/dcos/dcos-cli/pkg/setup"
	"github.com/spf13/cobra"
)

// newCmdClusterLink links the attached cluster to another one.
func newCmdClusterLink(ctx api.Context) *cobra.Command {
	setupFlags := setup.NewFlags(ctx.Fs(), ctx.EnvLookup)
	cmd := &cobra.Command{
		Use:  "link",
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			attachedCluster, err := ctx.Cluster()
			if err != nil {
				return err
			}

			manager := ctx.ConfigManager()
			linkableClusterConfig, err := manager.Find(args[0], false)
			if err != nil {
				if err == config.ErrConfigNotFound {
					msg := " is not set up in the CLI, would you like to do it now?"
					err = ctx.Prompt().Confirm(args[0] + msg)
					if err != nil {
						return err
					}

					// We do not want to attach the linkable cluster.
					attach := false
					ctx.Setup(setupFlags, args[0], attach)
				} else {
					return err
				}
			}

			if attachedCluster.Config().Path() == linkableClusterConfig.Path() {
				return errors.New("cannot link a cluster to itself")
			}

			linkableCluster := config.NewCluster(linkableClusterConfig)

			client := login.NewClient(ctx.HTTPClient(linkableCluster), ctx.Logger())
			rawProviders, err := client.Providers()
			if err != nil {
				return err
			}
			providers := rawProviders.Slice()
			var filteredProviders []*login.Provider

			// Not all login providers are supported for a cluster link.
			for _, provider := range providers {
				switch provider.Type {
				case login.DCOSUIDPassword, login.DCOSUIDPasswordLDAP,
					login.SAMLSpInitiated, login.OIDCAuthCodeFlow:
					filteredProviders = append(filteredProviders, provider)
				}
			}

			// We do not use a login.Flow as we are not following the entire flow.
			var provider *login.Provider
			switch len(filteredProviders) {
			case 0:
				return errors.New("couldn't determine a login provider")
			case 1:
				// Implicit provider selection.
				provider = filteredProviders[0]
			default:
				// Manual provider selection.
				prompt := ctx.Prompt()
				i, err := prompt.Select("Please select a login method:", filteredProviders)
				if err != nil {
					return err
				}
				provider = filteredProviders[i]
			}

			linkRequest := &clusterlinker.LinkRequest{
				ID:   linkableCluster.ID(),
				Name: linkableCluster.Name(),
				URL:  linkableCluster.URL(),
				LoginProvider: clusterlinker.LoginProvider{
					ID:   provider.ID,
					Type: provider.Type,
				},
			}

			attachedClient := clusterlinker.NewClient(ctx.HTTPClient(attachedCluster), ctx.Logger())
			return attachedClient.Link(linkRequest)
		},
	}
	setupFlags.Register(cmd.Flags())
	return cmd
}
