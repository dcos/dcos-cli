package cmd

import (
	"encoding/json"
	"errors"
	"fmt"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
	"os"
)

// These are the different auth types that DC/OS supports with the names that they'll be given from the providers
// endpoint.
const (
	AuthTypeDCOSUidPassword = "dcos-uid-password"
	AuthTypeDCOSUidServiceKey = "dcos-uid-servicekey"
	AuthTypeDCOSUidPasswordLDAP = "dcos-uid-password-ldap"
	AuthTypeSAMLSpInitiated = "saml-sp-initiated"
	AuthTypeOIDCAuthCodeFlow = "oidc-authorization-code-flow"
	AuthTypeOIDCImplicitFlow = "oidc-implicit-flow"
)

var jsonOutput bool

// authCmd represents the `dcos auth` subcommand.
var authListProvidersCmd = &cobra.Command{
	Use: "list-providers",
	Run: listProviders,
}

func init() {
	authCmd.AddCommand(authListProvidersCmd)
	authListProvidersCmd.Flags().BoolVar(&jsonOutput, "json", false,
		"returns providers in json format")
}

func listProviders(cmd *cobra.Command, args []string) {
	providers, err := getProviders()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	if jsonOutput {
		// re-marshal it into json with indents added in for pretty printing
		out, err := json.MarshalIndent(providers, "", "\t")
		if err != nil {
			fmt.Println(err)
			os.Exit(1)
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
			desc, err := authTypeDescription(provider.AuthenticationType, provider)
			if err != nil {
				fmt.Printf("Unknown authentication type %s", provider.AuthenticationType)
				os.Exit(1)
			}
			table.Append([]string{name, desc})
		}
		table.Render()
	}
}

func getProviders() (*map[string]authProvider, error) {
	var config = dcosConfig.Config
	var client = httpclient.New(config)
	var response, err = client.Get("/acs/api/v1/auth/providers")
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()

	var resp map[string]authProvider
	err = json.NewDecoder(response.Body).Decode(&resp)
	if err != nil {
		return nil, err
	}

	return &resp, nil
}

func authTypeDescription(authType string, provider authProvider) (string, error) {
	var desc string
	switch authType {
	case AuthTypeDCOSUidPassword:
		desc = "Log in using a standard DC/OS user account (username and password)"
	case AuthTypeDCOSUidServiceKey:
		desc = "Log in using a DC/OS service user account (username and private key)"
	case AuthTypeDCOSUidPasswordLDAP:
		desc = "Log in in using an LDAP user account (username and password)"
	case AuthTypeSAMLSpInitiated:
		desc = fmt.Sprintf("Log in using SAML 2.0 (%s)", provider.Description)
	case AuthTypeOIDCImplicitFlow:
		desc = fmt.Sprintf("Log in using OpenID Connect(%s)", provider.Description)
	case AuthTypeOIDCAuthCodeFlow:
		desc = fmt.Sprintf("Log in using OpenID Connect(%s)", provider.Description)
	default:
		return "", errors.New("unknown authentication type")
	}
	return desc, nil
}

type authProvider struct {
	AuthenticationType string                 `json:"authentication-type"`
	ClientMethod       string                 `json:"client-method"`
	Config             authListProviderConfig `json:"config"`
	Description        string                 `json:"description"`
}

type authListProviderConfig struct {
	StartFlowUrl string `json:"start_flow_url"`
}
