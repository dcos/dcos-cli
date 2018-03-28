package cmd

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"

	"github.com/dcos/dcos-cli/pkg/httpclient"
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

var jsonOutput bool

// authCmd represents the `dcos auth` subcommand.
var authListProvidersCmd = &cobra.Command{
	Use: "list-providers",
	RunE: listProviders,
}

func init() {
	authCmd.AddCommand(authListProvidersCmd)
	authListProvidersCmd.Flags().BoolVar(&jsonOutput, "json", false, "returns providers in json format")
}

func listProviders(cmd *cobra.Command, args []string) error {
	providers, err := getProviders()
	if err != nil {
		return err
	}

	if jsonOutput {
		// re-marshal it into json with indents added in for pretty printing
		out, err := json.MarshalIndent(providers, "", "\t")
		if err != nil {
			return err
		}
		fmt.Println(string(out))
	} else {
		table := tablewriter.NewWriter(os.Stdout)
		table.SetHeader([]string{"PROVIDER ID", "AUTHENTICATION TYPE"})
		// turn off wrapping because it seems to wrap even if the column is set to be wide enough
		table.SetAutoWrapText(false)
		table.SetBorder(false)
		table.SetRowSeparator(" ")
		table.SetColumnSeparator(" ")
		table.SetCenterSeparator(" ")

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
}

func getProviders() (*map[string]loginProvider, error) {
	config := dcosConfig.Config
	client := httpclient.New(config)
	response, err := client.Get("/acs/api/v1/auth/providers")
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()

	var resp map[string]loginProvider
	err = json.NewDecoder(response.Body).Decode(&resp)
	if err != nil {
		return nil, err
	}

	return &resp, nil
}

func loginTypeDescription(loginType string, provider loginProvider) (string, error) {
	var desc string
	switch loginType {
	case LoginTypeDCOSUidPassword:
		desc = "Log in using a standard DC/OS user account (username and password)"
	case LoginTypeDCOSUidServiceKey:
		desc = "Log in using a DC/OS service user account (username and private key)"
	case LoginTypeDCOSUidPasswordLDAP:
		desc = "Log in in using an LDAP user account (username and password)"
	case LoginTypeSAMLSpInitiated:
		desc = fmt.Sprintf("Log in using SAML 2.0 (%s)", provider.Description)
	case LoginTypeOIDCImplicitFlow:
		desc = fmt.Sprintf("Log in using OpenID Connect(%s)", provider.Description)
	case LoginTypeOIDCAuthCodeFlow:
		desc = fmt.Sprintf("Log in using OpenID Connect(%s)", provider.Description)
	default:
		return "", errors.New("unknown login provider")
	}
	return desc, nil
}

type loginProvider struct {
	AuthenticationType string                  `json:"authentication-type"`
	ClientMethod       string                  `json:"client-method"`
	Config             loginListProviderConfig `json:"config"`
	Description        string                  `json:"description"`
}

type loginListProviderConfig struct {
	StartFlowUrl string `json:"start_flow_url"`
}
