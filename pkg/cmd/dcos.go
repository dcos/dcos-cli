// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/sirupsen/logrus"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cmd/auth"
	clustercmd "github.com/dcos/dcos-cli/pkg/cmd/cluster"
	"github.com/dcos/dcos-cli/pkg/cmd/completion"
	configcmd "github.com/dcos/dcos-cli/pkg/cmd/config"
	plugincmd "github.com/dcos/dcos-cli/pkg/cmd/plugin"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/cosmos"
	"github.com/dcos/dcos-cli/pkg/internal/corecli"
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
		configcmd.NewCommand(ctx),
		clustercmd.NewCommand(ctx),
		plugincmd.NewCommand(ctx),
		completion.NewCommand(ctx),
	)

	// If a cluster is attached, we get its plugins.
	var hasCorePlugin bool
	if cluster, err := ctx.Cluster(); err == nil {
		pluginManager := ctx.PluginManager(cluster)
		for _, plugin := range pluginManager.Plugins() {
			if plugin.Name == "dcos-core-cli" {
				hasCorePlugin = true
			}
			for _, pluginCmd := range plugin.Commands {
				cmd.AddCommand(newPluginCommand(ctx, pluginCmd, false))
			}
		}
		cmd.SetHelpCommand(customHelpCommand(ctx, cmd, pluginManager.Plugins()))
	}

	// When the dcos-core-cli plugin is not installed, we add dummy core commands
	// based on data from the bundled core plugin. This will populate the help menu.
	if !hasCorePlugin {
		corePlugin, err := corecli.TempPlugin()
		if err == nil {
			for _, pluginCmd := range corePlugin.Commands {
				cmd.AddCommand(newPluginCommand(ctx, pluginCmd, true))
			}
		}
		cmd.SetHelpCommand(customHelpCommand(ctx, cmd, []*plugin.Plugin{corePlugin}))
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

func newPluginCommand(ctx api.Context, cmd plugin.Command, isDummyCoreCommand bool) *cobra.Command {
	return &cobra.Command{
		Use:                cmd.Name,
		Short:              cmd.Description,
		DisableFlagParsing: true,
		SilenceErrors:      true, // Silences error message if command returns an exit code.
		SilenceUsage:       true, // Silences usage information from the wrapper CLI on error.
		RunE: func(_ *cobra.Command, _ []string) error {
			// We don't support global plugins right now so no plugin should be run without a cluster.
			cluster, err := ctx.Cluster()
			if err != nil {
				ctx.Logger().Error("Error: no cluster is attached")
				return err
			}

			// Extract the bundled core plugin when the user is trying to run a dummy core command.
			if isDummyCoreCommand {
				corePlugin, err := extractCorePlugin(ctx, cluster)
				if err != nil {
					return err
				}
				for _, coreCmd := range corePlugin.Commands {
					if coreCmd.Name == cmd.Name {
						cmd = coreCmd
						break
					}
				}
			}

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

			return invokePlugin(ctx, cmd, cmdArgs)
		},
	}
}

func customHelpCommand(ctx api.Context, root *cobra.Command, plugins []*plugin.Plugin) *cobra.Command {
	return &cobra.Command{
		Use:   "help [command]",
		Short: "Help about any command",
		Long: `Help provides help for any command in the application.
		Simply type ` + root.Name() + ` help [path to command] for full details.`,
		DisableFlagParsing: true,

		Run: func(c *cobra.Command, args []string) {
			cmd, remArgs, e := c.Root().Find(args)
			if cmd == nil || e != nil {
				c.Printf("Unknown help topic %#q\n", args)
				c.Root().Usage()
			} else {
				for _, p := range plugins {
					for _, pluginCmd := range p.Commands {
						if cmd.Name() == pluginCmd.Name {
							args := []string{pluginCmd.Name}
							args = append(args, remArgs...)
							args = append(args, "--help")
							_ = invokePlugin(ctx, pluginCmd, args)
							return
						}
					}
				}
				cmd.InitDefaultHelpFlag() // make possible 'help' flag to be shown
				cmd.Help()
			}
		},
	}

}

// extractCorePlugin extracts the bundled core plugin into the plugins folder.
func extractCorePlugin(ctx api.Context, cluster *config.Cluster) (*plugin.Plugin, error) {
	ctx.Logger().Warn(`Extracting "dcos-core-cli"...`)

	pluginManager := ctx.PluginManager(cluster)
	err := corecli.InstallPlugin(ctx.Fs(), pluginManager)
	if err != nil {
		return nil, err
	}
	return pluginManager.Plugin("dcos-core-cli")
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

func invokePlugin(ctx api.Context, cmd plugin.Command, args []string) error {
	// We don't support global plugins right now so no plugin should be run without
	// a cluster.
	// This helps with the tempCore hack we're doing above to make it look like the
	// CLI has all the commands normally available when attached to a cluster but without
	// letting you actually run the commands until you've attached to a cluster.
	_, err := ctx.Cluster()
	if err != nil {
		ctx.Logger().Error("Error: no cluster is attached")
		return err
	}

	executablePath, err := os.Executable()
	if err != nil {
		return err
	}
	execCmd := exec.Command(cmd.Path, args...)
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

	// Pass cluster specific env variables when a cluster is attached.
	if cluster, err := ctx.Cluster(); err == nil {
		execCmd.Env = append(execCmd.Env, "DCOS_URL="+cluster.URL())
		execCmd.Env = append(execCmd.Env, "DCOS_ACS_TOKEN="+cluster.ACSToken())

		insecure := cluster.TLS().Insecure || strings.HasPrefix(cluster.URL(), "http://")
		if insecure {
			execCmd.Env = append(execCmd.Env, "DCOS_TLS_INSECURE=1")
		} else if cluster.TLS().RootCAsPath != "" {
			execCmd.Env = append(execCmd.Env, "DCOS_TLS_CA_PATH="+cluster.TLS().RootCAsPath)
		}
	}
	err = execCmd.Run()
	if err != nil {
		// Because we're silencing errors through Cobra, we need to print this separately.
		ctx.Logger().Debug(err)
	}
	return err
}
