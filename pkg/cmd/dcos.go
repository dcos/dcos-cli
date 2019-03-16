// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/antihax/optional"
	dcosclient "github.com/dcos/client-go/dcos"
	"github.com/sirupsen/logrus"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cmd/auth"
	clustercmd "github.com/dcos/dcos-cli/pkg/cmd/cluster"
	"github.com/dcos/dcos-cli/pkg/cmd/completion"
	configcmd "github.com/dcos/dcos-cli/pkg/cmd/config"
	plugincmd "github.com/dcos/dcos-cli/pkg/cmd/plugin"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/internal/corecli"
	"github.com/dcos/dcos-cli/pkg/internal/cosmos"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/spf13/afero"
	"github.com/spf13/cobra"
)

const annotationUsageOptions string = "usage_options"

// NewDCOSCommand creates the `dcos` command with its `auth`, `config`, and `cluster` subcommands.
func NewDCOSCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "dcos",
		Args: cobra.ArbitraryArgs,
		PersistentPreRun: func(cmd *cobra.Command, args []string) {
			cmd.SilenceUsage = true
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			switch args[0] {
			case "job", "marathon", "node", "package", "service", "task":
				cluster, err := ctx.Cluster()
				if err != nil {
					return config.ErrNotAttached
				}
				corePlugin, err := extractCorePlugin(ctx, cluster)
				if err != nil {
					return err
				}
				for _, coreCmd := range corePlugin.Commands {
					if coreCmd.Name == args[0] {
						return newPluginCommand(ctx, coreCmd).RunE(nil, nil)
					}
				}
			}
			return fmt.Errorf("unknown command %s", args[0])
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
	if cluster, err := ctx.Cluster(); err == nil {
		pluginManager := ctx.PluginManager(cluster)
		for _, plugin := range pluginManager.Plugins() {
			for _, pluginCmd := range plugin.Commands {
				cmd.AddCommand(newPluginCommand(ctx, pluginCmd))
			}
		}
	}

	// This follows the CLI design guidelines for help formatting.
	cmd.SetUsageTemplate(`Usage:{{if .HasAvailableSubCommands}}
  {{.CommandPath}} [command]{{else if .Runnable}}
  {{.UseLine}}{{end}}{{if .HasExample}}

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
	pluginCmd := &cobra.Command{
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

			return invokePlugin(ctx, cmd, cmdArgs)
		},
	}
	pluginCmd.SetHelpFunc(func(_ *cobra.Command, cmdArgs []string) {
		args := []string{cmd.Name}
		args = append(args, cmdArgs...)
		args = append(args, "--help")
		invokePlugin(ctx, cmd, args)
	})
	return pluginCmd
}

// extractCorePlugin extracts the bundled core plugin into the plugins folder.
func extractCorePlugin(ctx api.Context, cluster *config.Cluster) (*plugin.Plugin, error) {
	pluginManager := ctx.PluginManager(cluster)
	err := corecli.InstallPlugin(ctx.Fs(), pluginManager, ctx.Deprecated)
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

	// Get package information from Cosmos.
	cosmosClient, err := cosmos.NewClient()
	if err != nil {
		return err
	}
	pkg, _, err := cosmosClient.PackageDescribe(context.TODO(), &dcosclient.PackageDescribeOpts{
		PackageDescribeRequest: optional.NewInterface(dcosclient.PackageDescribeRequest{
			PackageName: "dcos-core-cli",
		}),
	})
	if err != nil {
		return err
	}

	pluginInfo, err := cosmos.CLIPluginInfo(pkg, ctx.HTTPClient(cluster).BaseURL())
	if err != nil {
		return err
	}

	return ctx.PluginManager(cluster).Install(pluginInfo.Url, &plugin.InstallOpts{
		Name:   "dcos-core-cli",
		Update: true,
		PostInstall: func(fs afero.Fs, pluginDir string) error {
			pkgInfoFilepath := filepath.Join(pluginDir, "package.json")
			pkgInfoFile, err := fs.OpenFile(pkgInfoFilepath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
			if err != nil {
				return err
			}
			defer pkgInfoFile.Close()
			return json.NewEncoder(pkgInfoFile).Encode(pkg.Package)
		},
	})
}

// invokePlugin calls the binary of a plugin, passing in the arguments it's been given.
func invokePlugin(ctx api.Context, cmd plugin.Command, args []string) error {
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

		// When the plugin command exits with a non-zero code, the main CLI process
		// exit code should be the same.
		//
		// see https://jira.mesosphere.com/browse/DCOS_OSS-4399
		if exiterr, ok := err.(*exec.ExitError); ok {
			if status, ok := exiterr.Sys().(syscall.WaitStatus); ok {
				// TODO: have a more generic error handling system
				// where errors can be associated with an exit code.
				os.Exit(status.ExitStatus())
			}
		}
	}
	return err
}
