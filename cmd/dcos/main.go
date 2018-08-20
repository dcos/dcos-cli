package main

import (
	"fmt"
	"io/ioutil"
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
	"github.com/spf13/afero"
	"github.com/spf13/pflag"
)

func main() {
	ctx := cli.NewContext(&cli.Environment{
		Args:      os.Args,
		Input:     os.Stdin,
		Out:       os.Stdout,
		ErrOut:    os.Stderr,
		EnvLookup: os.LookupEnv,
		Fs:        afero.NewOsFs(),
	})

	if err := run(ctx, os.Args); err != nil {
		os.Exit(1)
	}
}

// run launches the DC/OS CLI with a given context and args.
func run(ctx api.Context, args []string) error {
	var verbosity int
	var debug bool
	var logLevel string
	var showVersion bool

	// Register the version and verbose global flags.
	// We ContinueOnError because we don't want to fail for subcommand specific flags.
	// We discard any output because we don't want the `-h` flag to trigger usage on this flagset.
	globalFlags := pflag.NewFlagSet(args[0], pflag.ContinueOnError)
	globalFlags.SetOutput(ioutil.Discard)
	globalFlags.BoolVar(&showVersion, "version", false, "")
	globalFlags.CountVarP(&verbosity, "", "v", "")
	globalFlags.BoolVar(&debug, "debug", false, "")
	globalFlags.StringVar(&logLevel, "log-level", "", "")
	globalFlags.Parse(args[1:])

	if verbosity == 0 {
		if envVerbosity, ok := ctx.EnvLookup("DCOS_VERBOSITY"); ok {
			verbosity, _ = strconv.Atoi(envVerbosity)
		}
	}
	if debug {
		logLevel = "debug"
		fmt.Fprintln(os.Stderr, "The --debug flag is deprecated. Please use the -vv flag.")
	}
	ctx.Logger().SetLevel(logrusLevel(verbosity, logLevel))

	if showVersion {
		printVersion(ctx)
		return nil
	}
	return cmd.NewDCOSCommand(ctx).Execute()
}

// logLevel returns the log level for the CLI based on the verbosity. The default verbosity is 0.
func logrusLevel(verbosity int, logLevel string) logrus.Level {
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
		fmt.Fprintln(os.Stderr, "The --log-level flag is deprecated. Please use the -vv flag.")
		return logrus.DebugLevel
	case "info", "warning":
		fmt.Fprintln(os.Stderr, "The --log-level flag is deprecated. Please use the -v flag.")
		return logrus.InfoLevel
	case "error", "critical":
		fmt.Fprintf(os.Stderr, "The --log-level=%s flag is deprecated. It is enabled by default.\n", logLevel)
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
