package main

import (
	"fmt"
	"io"
	"os"
	"strconv"
	"time"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cli/version"
	"github.com/dcos/dcos-cli/pkg/cmd"
	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
)

func main() {
	if err := run(cli.NewOsEnvironment()); err != nil {
		os.Exit(1)
	}
}

// run launches the DC/OS CLI with a given environment.
func run(env *cli.Environment) error {
	globalFlags := &cli.GlobalFlags{}
	env.Args = append(env.Args[:1], globalFlags.Parse(env.Args[1:])...)

	if globalFlags.Verbosity == 0 {
		if envVerbosity, ok := env.EnvLookup("DCOS_VERBOSITY"); ok {
			globalFlags.Verbosity, _ = strconv.Atoi(envVerbosity)
		}
	}
	if globalFlags.Debug {
		globalFlags.LogLevel = "debug"
		fmt.Fprintln(env.ErrOut, "The --debug flag is deprecated. Please use the -vv flag.")
	}

	ctx := cli.NewContext(env)
	ctx.Logger().SetLevel(logrusLevel(env.ErrOut, globalFlags.Verbosity, globalFlags.LogLevel))

	if globalFlags.Version {
		printVersion(ctx)
		return nil
	}
	dcosCmd := cmd.NewDCOSCommand(ctx)
	dcosCmd.SetArgs(env.Args[1:])
	return dcosCmd.Execute()
}

// logrusLevel returns the log level for the CLI based on the verbosity. The default verbosity is 0.
func logrusLevel(errout io.Writer, verbosity int, logLevel string) logrus.Level {
	if verbosity > 1 {
		// -vv sets the logger level to debug. This also happens for -vvv
		// and above, in such cases we set the logging level to its maximum.
		return logrus.DebugLevel
	}

	if verbosity == 1 {
		// -v sets the logger level to info.
		return logrus.InfoLevel
	}

	switch logLevel {
	case "debug":
		fmt.Fprintln(errout, "The --log-level flag is deprecated. Please use the -vv flag.")
		return logrus.DebugLevel
	case "info", "warning":
		fmt.Fprintln(errout, "The --log-level flag is deprecated. Please use the -v flag.")
		return logrus.InfoLevel
	case "error", "critical":
		fmt.Fprintf(errout, "The --log-level=%s flag is deprecated. It is enabled by default.\n", logLevel)
	}
	// Without the verbose flag, default to error level.
	return logrus.ErrorLevel
}

// printVersion prints CLI version information.
func printVersion(ctx api.Context) {
	fmt.Fprintln(ctx.Out(), "dcoscli.version="+version.Version())

	cluster, err := ctx.Cluster()
	if err != nil {
		return
	}

	dcosClient := dcos.NewClient(ctx.HTTPClient(cluster, httpclient.Timeout(3*time.Second)))
	if dcosVersion, err := dcosClient.Version(); err == nil {
		fmt.Fprintln(ctx.Out(), "dcos.version="+dcosVersion.Version)
		fmt.Fprintln(ctx.Out(), "dcos.commit="+dcosVersion.DCOSImageCommit)
		fmt.Fprintln(ctx.Out(), "dcos.bootstrap-id="+dcosVersion.BootstrapID)
	} else {
		fmt.Fprintln(ctx.Out(), "dcos.version=N/A")
		fmt.Fprintln(ctx.Out(), "dcos.commit=N/A")
		fmt.Fprintln(ctx.Out(), "dcos.bootstrap-id=N/A")
	}
}
