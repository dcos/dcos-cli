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
	"text/template"

	"github.com/antihax/optional"
	dcosclient "github.com/dcos/client-go/dcos"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/spf13/cobra"
	"github.com/spf13/pflag"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli/version"
	"github.com/dcos/dcos-cli/pkg/cmd/auth"
	clustercmd "github.com/dcos/dcos-cli/pkg/cmd/cluster"
	"github.com/dcos/dcos-cli/pkg/cmd/completion"
	configcmd "github.com/dcos/dcos-cli/pkg/cmd/config"
	plugincmd "github.com/dcos/dcos-cli/pkg/cmd/plugin"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/internal/cosmos"
	"github.com/dcos/dcos-cli/pkg/plugin"
)

const annotationUsageOptions string = `    --version
        Print version information
    -v, -vv
        Output verbosity (verbose or very verbose)
    -h, --help
        Show usage help`

// NewDCOSCommand creates the `dcos` command with its `auth`, `config`, and `cluster` subcommands.
func NewDCOSCommand(ctx api.Context) *cobra.Command {
	cmd := &cobra.Command{
		Use:  "dcos",
		Args: cobra.ArbitraryArgs,
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

	cmd.SetUsageFunc(helpMenuFunc)
	cmd.SilenceUsage = true

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
		CosmosPackageDescribeV1Request: optional.NewInterface(dcosclient.CosmosPackageDescribeV1Request{
			PackageName: "dcos-core-cli",
		}),
	})
	if err != nil {
		return err
	}

	httpClient, err := ctx.HTTPClient(cluster)
	if err != nil {
		return err
	}
	pluginInfo, err := cosmos.CLIPluginInfo(pkg, httpClient.BaseURL())
	if err != nil {
		return err
	}

	_, err = ctx.PluginManager(cluster).Install(pluginInfo.Url, &plugin.InstallOpts{
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
	return err
}

// invokePlugin calls the binary of a plugin, passing in the arguments it's been given.
func invokePlugin(ctx api.Context, cmd plugin.Command, args []string) error {
	execCmd := exec.Command(cmd.Path, args...) // nolint: gosec
	execCmd.Stdout = ctx.Out()
	execCmd.Stderr = ctx.ErrOut()
	execCmd.Stdin = ctx.Input()

	executablePath, err := os.Executable()
	if err != nil {
		return err
	}
	cluster, err := ctx.Cluster()
	if err != nil && err != config.ErrNotAttached {
		return err
	}
	if cluster != nil {
		_, err := cluster.TLS()
		if err != nil {
			return fmt.Errorf("ssl_verify configuration is invalid: %s", err)
		}
	}
	execCmdEnv := pluginEnv(executablePath, cmd.Name, ctx.Logger().Level, cluster)
	execCmd.Env = append(os.Environ(), execCmdEnv...)

	err = execCmd.Run()
	if err != nil {
		// Because we're silencing errors through Cobra, we need to print this separately.
		ctx.Logger().Debug(err)
		// When the plugin command exits with a non-zero code, the main CLI process
		// exit code should be the same. ExitCode() returns -1 if the process
		// hasn't exited or was terminated by a signal thus we have to check.
		//
		// See https://jira.mesosphere.com/browse/DCOS_OSS-4399
		if exitCode := execCmd.ProcessState.ExitCode(); exitCode > 0 {
			os.Exit(exitCode)
		}

	}
	return err
}

// pluginEnv returns the environment variables to pass to a given plugin.
func pluginEnv(executablePath string, cmdName string, logLevel logrus.Level, cluster *config.Cluster) (env []string) {
	env = append(env, "DCOS_CLI_EXECUTABLE_PATH="+executablePath)
	env = append(env, "DCOS_CLI_VERSION="+version.Version())

	switch logLevel {
	case logrus.DebugLevel:
		env = append(env, "DCOS_VERBOSITY=2", "DCOS_LOG_LEVEL=debug")
	case logrus.InfoLevel:
		env = append(env, "DCOS_VERBOSITY=1", "DCOS_LOG_LEVEL=info")
	}

	// Pass cluster specific env variables when a cluster is attached.
	if cluster != nil {
		env = append(env, "DCOS_URL="+cluster.URL())
		env = append(env, "DCOS_ACS_TOKEN="+cluster.ACSToken())

		// Create env entries based on the subcommand config.
		if cmdConfig, ok := cluster.Config().ToMap()[cmdName].(map[string]interface{}); ok {
			for key, val := range cmdConfig {
				env = append(env, fmt.Sprintf(
					"%s=%v",
					cmdConfigEnvKey(cmdName, key),
					val,
				))
			}
		}

		clusterTLS, _ := cluster.TLS()
		insecure := clusterTLS.Insecure || strings.HasPrefix(cluster.URL(), "http://")
		if insecure {
			env = append(env, "DCOS_TLS_INSECURE=1")
		} else if clusterTLS.RootCAsPath != "" {
			env = append(env, "DCOS_TLS_CA_PATH="+clusterTLS.RootCAsPath)
		}
	}
	return env
}

// cmdConfigEnvKey returns the environment variable key to use for a given command config.
//
// For example, it will return `DCOS_HELLO_WORLD` for a config named `hello.world`.
func cmdConfigEnvKey(cmdName, configKey string) string {
	return fmt.Sprintf(
		"DCOS_%s_%s",
		strings.ToUpper(strings.ReplaceAll(cmdName, "-", "_")),
		strings.ToUpper(configKey),
	)
}

// help menu template that follow UX styleguide.
func helpMenuFunc(command *cobra.Command) error {
	tpl := template.New("top")
	template.Must(tpl.Parse(`Usage:{{if .HasAvailableSubCommands}}
    {{.CommandPath}} [command]{{else if .Runnable}}
    {{.UseLine}}{{end}}{{if .HasExample}}

Examples:
    {{.Example}}{{end}}{{if .HasAvailableSubCommands}}

Commands:{{range .Commands}}{{if (or .IsAvailableCommand (eq .Name "help"))}}
    {{.Name}}
        {{.Short}}{{end}}{{end}}{{end}}
`))

	err := tpl.Execute(command.OutOrStdout(), command)
	if err != nil {
		return err
	}

	fmt.Fprintln(command.OutOrStdout(), "\nOptions:")
	if command.Use == "dcos" {
		fmt.Fprintln(command.OutOrStdout(), annotationUsageOptions)
	} else if command.HasAvailableLocalFlags() {
		command.LocalFlags().VisitAll(func(f *pflag.Flag) {
			if f.Hidden {
				return
			}
			if f.Shorthand != "" && f.Name != "" {
				fmt.Fprintf(command.OutOrStdout(), "    -%s, --%s\n", f.Shorthand, f.Name)
			} else if f.Shorthand != "" {
				fmt.Fprintf(command.OutOrStdout(), "    -%s\n", f.Shorthand)
			} else {
				fmt.Fprintf(command.OutOrStdout(), "    --%s\n", f.Name)
			}
			fmt.Fprintln(command.OutOrStdout(), "        "+f.Usage)
		})
	}

	if command.HasAvailableSubCommands() {
		fmt.Fprintln(command.OutOrStdout(), "\n"+`Use "`+command.CommandPath()+` [command] --help" for more information about a command.`)
	}
	return nil
}
