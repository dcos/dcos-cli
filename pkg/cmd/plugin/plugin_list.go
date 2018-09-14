package plugin

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// newCmdPluginList creates the `dcos plugin list` subcommand.
func newCmdPluginList(ctx api.Context) *cobra.Command {
	var jsonOutput bool
	var commands bool
	var completionDirs bool
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List CLI plugins",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			cluster, err := ctx.Cluster()
			if err != nil {
				return err
			}

			plugins := ctx.PluginManager(cluster).Plugins()

			if jsonOutput {
				enc := json.NewEncoder(ctx.Out())
				enc.SetIndent("", "    ")
				return enc.Encode(plugins)
			} else if commands {
				for _, plugin := range plugins {
					for _, command := range plugin.Commands {
						fmt.Fprintf(ctx.Out(), "%s ", command.Name)
					}
				}
				return nil
			} else if completionDirs {
				for _, plugin := range plugins {
					fmt.Fprintf(ctx.Out(), "%s ", plugin.CompletionDir())
				}
				return nil
			}

			table := cli.NewTable(ctx.Out(), []string{"NAME", "COMMANDS"})
			for _, plugin := range plugins {
				var commands []string
				for _, command := range plugin.Commands {
					commands = append(commands, command.Name)
				}
				table.Append([]string{plugin.Name, strings.Join(commands, " ")})
			}
			table.Render()
			return nil
		},
	}
	cmd.Flags().BoolVar(&jsonOutput, "json", false, "Print plugins in JSON format.")
	cmd.Flags().BoolVar(&commands, "commands", false,
		"Prints out a list of the commands available through plugins")
	cmd.Flags().BoolVar(&completionDirs, "completion-dirs", false,
		"Prints out a list of the completion scripts for the currently available plugins")

	cmd.Flags().MarkHidden("commands")
	cmd.Flags().MarkHidden("completion-dirs")
	return cmd
}
