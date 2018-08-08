// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"os/exec"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cmd/auth"
	"github.com/dcos/dcos-cli/pkg/cmd/cluster"
	"github.com/dcos/dcos-cli/pkg/cmd/completion"
	"github.com/dcos/dcos-cli/pkg/cmd/config"
	plugincmd "github.com/dcos/dcos-cli/pkg/cmd/plugin"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/spf13/cobra"
)

const annotationUsageOptions string = "usage_options"

// NewDCOSCommand creates the `dcos` command with its `auth`, `config`, and `cluster` subcommands.
func NewDCOSCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use: "dcos",
		PersistentPreRun: func(cmd *cobra.Command, args []string) {
			cmd.SilenceUsage = true
		},
	}

	// This global flag is handled outside of cobra. It is declared here to prevent the unknown flag error.
	cmd.PersistentFlags().CountP("", "v", "")

	cmd.AddCommand(
		auth.NewCommand(ctx),
		config.NewCommand(ctx),
		cluster.NewCommand(ctx),
		plugincmd.NewCommand(ctx),
		completion.NewCommand(ctx),
	)

	// If a cluster is attached, we get its plugins.
	if cluster, err := ctx.Cluster(); err == nil {
		pluginManager := ctx.PluginManager(cluster)

		for _, plugin := range pluginManager.Plugins() {
			for _, pluginCmd := range plugin.Commands {
				cmd.AddCommand(newPluginCommand(ctx, pluginCmd))
			}
		}
	}

	// This follows the CLI design guidelines for help formatting.
	cmd.SetUsageTemplate(`Usage:{{if .Runnable}}
  {{.UseLine}}{{end}}{{if .HasAvailableSubCommands}}
  {{.CommandPath}} [command]{{end}}{{if .HasExample}}

Examples:
{{.Example}}{{end}}{{if .HasAvailableSubCommands}}

Commands:{{range .Commands}}{{if (or .IsAvailableCommand (eq .Name "help"))}}
  {{.Name}}
      {{.Short}}{{end}}{{end}}{{end}}{{if .HasAvailableLocalFlags}}

Options:{{if ne (index .Annotations "` + annotationUsageOptions + `") ""}}{{index .Annotations "` + annotationUsageOptions + `"}}{{else}}
{{.LocalFlags.FlagUsages | trimTrailingWhitespaces}}{{end}}{{end}}{{if .HasAvailableSubCommands}}

Use "{{.CommandPath}} [command] --help" for more information about a command.{{end}}
`)

	cmd.Annotations = map[string]string{
		annotationUsageOptions: `
  --version
      Print version information
  -v, -vv
      Output verbosity (verbose or very verbose)
  -h, --help
      Show usage help`,
	}

	return cmd
}

func newPluginCommand(ctx api.Context, cmd plugin.Command) *cobra.Command {
	return &cobra.Command{
		Use:                cmd.Name,
		Short:              cmd.Description,
		DisableFlagParsing: true,
		SilenceErrors:      true, // Silences error message if command returns an exit code.
		SilenceUsage:       true, // Silences usage information from the wrapper CLI on error.
		RunE: func(_ *cobra.Command, _ []string) error {
			// Extract the specific arguments of a command from the context.
			ctxArgs := ctx.Args()
			var cmdArgs []string
			for key, arg := range ctxArgs {
				if arg == cmd.Name {
					cmdArgs = ctxArgs[key:]
				}
			}

			execCmd := exec.Command(cmd.Path, cmdArgs...)
			execCmd.Stdout = ctx.Out()
			execCmd.Stderr = ctx.ErrOut()
			execCmd.Stdin = ctx.Input()

			err := execCmd.Run()
			if err != nil {
				// Because we're silencing errors through Cobra, we need to print this separately.
				ctx.Logger().Debug(err)
			}
			return err
		},
	}
}
