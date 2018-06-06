package cluster

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/url"

	"github.com/dcos/dcos-cli/api"
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

			var linkableCluster config.Cluster
			for _, cluster := range ctx.Clusters() {
				if args[0] == cluster.ID() ||
					args[0] == cluster.URL() ||
					args[0] == cluster.Name() && ctx.IsUniqueCluster(cluster.Name()) {
					linkableCluster = *cluster
					break
				}
			}

			if (config.Cluster{}) == linkableCluster {
				// The cluster does not exist yet. Two possibilities:
				// - The argument is an URL, we try to setup the cluster.
				// - The argument is not an URL, we return an error.
				_, err = url.ParseRequestURI(args[0])
				if err != nil {
					return errors.New("unable to retrieve cluster " + args[0])
				}

				msg := " is not set up in the CLI, would you like to do it now?"
				err = ctx.Prompt().Confirm(args[0] + msg)
				if err != nil {
					return err
				}

				// We save the current configuration before starting the setup.
				manager := ctx.ConfigManager()
				conf, err := manager.Current()
				if err != nil {
					return err
				}
				ctx.Setup(setupFlags, args[0])

				// The new cluster is set up and attached, we reattach the old one.
				newlyAttachedCluster, err := ctx.Cluster()
				if err != nil {
					return err
				}
				linkableCluster = *newlyAttachedCluster
				manager.Attach(conf)
			}

			if attachedCluster.ID() == linkableCluster.ID() {
				return errors.New("cannot link a cluster to itself")
			}

			client := login.NewClient(ctx.HTTPClient(&linkableCluster), ctx.Logger())
			rawProviders, err := client.Providers()
			if err != nil {
				return err
			}
			providers := rawProviders.Slice()

			// We do not use a login.Flow as we are not following the entire flow.
			var provider *login.Provider
			switch len(providers) {
			case 0:
				return errors.New("couldn't determine a login provider")
			case 1:
				// Implicit provider selection.
				provider = providers[0]
			default:
				// Manual provider selection.
				prompt := ctx.Prompt()
				i, err := prompt.Select("Please select a login method:", providers)
				if err != nil {
					return err
				}
				provider = providers[i]
			}

			type LoginProvider struct {
				ID   string `json:"id"`
				Type string `json:"type"`
			}

			type LinkRequest struct {
				ID            string `json:"id"`
				Name          string `json:"name"`
				URL           string `json:"url"`
				LoginProvider `json:"login_provider"`
			}

			linkRequest := &LinkRequest{
				ID:   linkableCluster.ID(),
				Name: linkableCluster.Name(),
				URL:  linkableCluster.URL(),
				LoginProvider: LoginProvider{
					ID:   provider.ID,
					Type: provider.Type,
				},
			}
			message, err := json.Marshal(linkRequest)

			attachedClient := ctx.HTTPClient(attachedCluster)
			_, err = attachedClient.Post("/cluster/v1/links", "application/json", bytes.NewReader(message))
			if err != nil {
				return err
			}

			return nil
		},
	}
	setupFlags.Register(cmd.Flags())
	return cmd
}
