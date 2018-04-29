package auth

import (
	"encoding/json"
	"fmt"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/dcos/dcos-cli/pkg/render"
	"github.com/spf13/cobra"
)

// newCmdAuthListProviders creates the `dcos auth list-providers` subcommand.
func newCmdAuthListProviders(ctx *cli.Context) *cobra.Command {
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
				table := render.NewTable([]string{"PROVIDER ID", "AUTHENTICATION TYPE"})

				for name, provider := range providers {
					table.Append([]interface{}{name, provider.String()})
				}
				table.Render(ctx.Out())
			}

			return nil
		},
	}
	cmd.Flags().BoolVar(&jsonOutput, "json", false, "returns providers in json format")
	return cmd
}
