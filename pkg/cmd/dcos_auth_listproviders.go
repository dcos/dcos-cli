package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/spf13/cobra"
)

// These are the different auth types that DC/OS supports with the names that they'll be given from the providers
// endpoint.
const (
	LoginTypeDCOSUidPassword     = "dcos-uid-password"
	LoginTypeDCOSUidServiceKey   = "dcos-uid-servicekey"
	LoginTypeDCOSUidPasswordLDAP = "dcos-uid-password-ldap"
	LoginTypeSAMLSpInitiated     = "saml-sp-initiated"
	LoginTypeOIDCAuthCodeFlow    = "oidc-authorization-code-flow"
	LoginTypeOIDCImplicitFlow    = "oidc-implicit-flow"
)

// newCmdAuthListProviders creates the `dcos auth list-providers` subcommand.
func newCmdAuthListProviders(ctx *cli.Context) *cobra.Command {
	var jsonOutput bool
	cmd := &cobra.Command{
		Use:  "list-providers",
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var client *httpclient.Client
			if len(args) == 0 {
				cluster, err := ctx.Cluster()
				if err != nil {
					return err
				}
				client = ctx.HTTPClient(cluster)
			} else {
				client = httpclient.New(args[0])
			}

			providers, err := getProviders(client)
			if err != nil {
				return err
			}

			if jsonOutput {
				// Re-marshal it into json with indents added in for pretty printing.
				out, err := json.MarshalIndent(providers, "", "\t")
				if err != nil {
					return err
				}
				fmt.Fprintln(ctx.Out(), string(out))
			} else {
				table := cli.NewTable(ctx.Out(), []string{"PROVIDER ID", "AUTHENTICATION TYPE"})

				for name, provider := range *providers {
					desc, err := loginTypeDescription(provider.AuthenticationType, provider)
					if err != nil {
						return err
					}
					table.Append([]string{name, desc})
				}
				table.Render()
			}

			return nil
		},
	}
	cmd.Flags().BoolVar(&jsonOutput, "json", false, "returns providers in json format")
	return cmd
}

func getProviders(client *httpclient.Client) (*map[string]loginProvider, error) {
	response, err := client.Get("/acs/api/v1/auth/providers")
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()

	var resp map[string]loginProvider
	err = json.NewDecoder(response.Body).Decode(&resp)
	return &resp, err
}

func loginTypeDescription(loginType string, provider loginProvider) (string, error) {
	switch loginType {
	case LoginTypeDCOSUidPassword:
		return "Log in using a standard DC/OS user account (username and password)", nil
	case LoginTypeDCOSUidServiceKey:
		return "Log in using a DC/OS service user account (username and private key)", nil
	case LoginTypeDCOSUidPasswordLDAP:
		return "Log in in using an LDAP user account (username and password)", nil
	case LoginTypeSAMLSpInitiated:
		return fmt.Sprintf("Log in using SAML 2.0 (%s)", provider.Description), nil
	case LoginTypeOIDCImplicitFlow:
		return fmt.Sprintf("Log in using OpenID Connect(%s)", provider.Description), nil
	case LoginTypeOIDCAuthCodeFlow:
		return fmt.Sprintf("Log in using OpenID Connect(%s)", provider.Description), nil
	default:
		return "", fmt.Errorf("unknown login provider %s", loginType)
	}
}

type loginProvider struct {
	AuthenticationType string                  `json:"authentication-type"`
	ClientMethod       string                  `json:"client-method"`
	Config             loginListProviderConfig `json:"config"`
	Description        string                  `json:"description"`
}

type loginListProviderConfig struct {
	StartFlowURL string `json:"start_flow_url"`
}
