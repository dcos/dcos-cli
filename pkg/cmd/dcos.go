// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"

	"github.com/sirupsen/logrus"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cmd/auth"
	"github.com/dcos/dcos-cli/pkg/cmd/cluster"
	"github.com/dcos/dcos-cli/pkg/cmd/completion"
	"github.com/dcos/dcos-cli/pkg/cmd/config"
	plugincmd "github.com/dcos/dcos-cli/pkg/cmd/plugin"
	"github.com/dcos/dcos-cli/pkg/cosmos"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/spf13/afero"
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
      {{.Short}}{{end}}{{end}}{{end}}{{if or .HasAvailableLocalFlags (ne (index .Annotations "` + annotationUsageOptions + `") "")}}

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
					break
				}
			}

			if len(cmdArgs) >= 3 && cmdArgs[0] == "package" && cmdArgs[1] == "install" && cmdArgs[2] == "dcos-core-cli" {
				// This is a temporary fix in place for the core plugin not being able to update itself.
				// In the long-term we should come-up with an installation system which is able to update
				// running binary executables.
				//
				// https://jira.mesosphere.com/browse/DCOS_OSS-3985
				// https://unix.stackexchange.com/questions/138214/how-is-it-possible-to-do-a-live-update-while-a-program-is-running#answer-138241
				return updateCorePlugin(ctx)
			}

			executablePath, err := os.Executable()
			if err != nil {
				return err
			}
			execCmd := exec.Command(cmd.Path, cmdArgs...)
			execCmd.Stdout = ctx.Out()
			execCmd.Stderr = ctx.ErrOut()
			execCmd.Stdin = ctx.Input()

			execCmd.Env = append(os.Environ(), "DCOS_CLI_EXECUTABLE_PATH="+executablePath)

			switch ctx.Logger().Level {
			case logrus.DebugLevel:
				execCmd.Env = append(execCmd.Env, "DCOS_VERBOSITY=2", "DCOS_LOG_LEVEL=debug")
			case logrus.InfoLevel:
				execCmd.Env = append(execCmd.Env, "DCOS_VERBOSITY=1", "DCOS_LOG_LEVEL=info")
			}

			err = execCmd.Run()
			if err != nil {
				// Because we're silencing errors through Cobra, we need to print this separately.
				ctx.Logger().Debug(err)
			}
			return err
		},
	}
}

// updateCorePlugin updates the core CLI plugin.
func updateCorePlugin(ctx api.Context) error {
	cluster, err := ctx.Cluster()
	if err != nil {
		return err
	}
	httpClient := ctx.HTTPClient(cluster)

	// Get package information from Cosmos.
	pkgInfo, err := cosmos.NewClient(httpClient).DescribePackage("dcos-core-cli")
	if err != nil {
		return err
	}

	// Get the download URL for the current platform.
	p, ok := pkgInfo.Package.Resource.CLI.Plugins[runtime.GOOS]["x86-64"]
	if !ok {
		return fmt.Errorf("'dcos-core-cli' isn't available for '%s')", runtime.GOOS)
	}
	return ctx.PluginManager(cluster).Install(p.URL, &plugin.InstallOpts{
		Name:   "dcos-core-cli",
		Update: true,
		PostInstall: func(fs afero.Fs, pluginDir string) error {
			pkgInfoFilepath := filepath.Join(pluginDir, "package.json")
			pkgInfoFile, err := fs.OpenFile(pkgInfoFilepath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
			if err != nil {
				return err
			}
			defer pkgInfoFile.Close()
			return json.NewEncoder(pkgInfoFile).Encode(pkgInfo.Package)
		},
	})
}
