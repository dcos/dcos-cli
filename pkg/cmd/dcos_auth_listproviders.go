package cmd

import (
	"encoding/json"
	"fmt"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
	"os"
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
		table.SetBorder(false)
		table.SetRowSeparator(" ")
		table.SetColumnSeparator(" ")
		table.SetCenterSeparator(" ")

		for _, v := range *providers {
			table.Append([]string{v.AuthenticationType, v.Description})
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

type authProvider struct {
	AuthenticationType string                 `json:"authentication-type"`
	ClientMethod       string                 `json:"client-method"`
	Config             authListProviderConfig `json:"config"`
	Description        string                 `json:"description"`
}

type authListProviderConfig struct {
	StartFlowUrl string `json:"start_flow_url"`
}
