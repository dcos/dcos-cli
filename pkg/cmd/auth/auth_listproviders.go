package auth

import (
	"encoding/json"
	"fmt"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func newSubCmdAuthListProviders(ctx *cli.Context) subcommand.SubCommand {
	sc := subcommand.NewInternalCommand(newCmdAuthListProviders(ctx))
	return sc
}

// newCmdAuthListProviders creates the `dcos auth list-providers` subcommand.
func newCmdAuthListProviders(ctx api.Context) *cobra.Command {
	var jsonOutput bool
	cmd := &cobra.Command{
		Use:  "list-providers",
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var client *login.Client
			if len(args) == 0 {
				cluster, err := ctx.Cluster()
				if err != nil {
					return err
				}
				client = login.NewClient(ctx.HTTPClient(cluster), ctx.Logger())
			} else {
				httpClient := httpclient.New(args[0], httpclient.Logger(ctx.Logger()))
				client = login.NewClient(httpClient, ctx.Logger())
			}

			providers, err := client.Providers()
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
				table := cli.NewTable(ctx.Out(), []string{"PROVIDER ID", "LOGIN METHOD"})
				for _, provider := range providers.Slice() {
					table.Append([]string{provider.ID, provider.String()})
				}
				table.Render()
			}

			return nil
		},
	}
	cmd.Flags().BoolVar(&jsonOutput, "json", false, "returns providers in json format")
	return cmd
}
