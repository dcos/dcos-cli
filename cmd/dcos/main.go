package main

import (
	"fmt"
	"io/ioutil"
	"os"
	"os/user"
	"time"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cmd"
	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/spf13/pflag"
)

var version = "SNAPSHOT"

func main() {
	ctx := cli.NewContext(&cli.Environment{
		Input:      os.Stdin,
		Out:        os.Stdout,
		ErrOut:     os.Stderr,
		EnvLookup:  os.LookupEnv,
		UserLookup: user.Current,
		Fs:         afero.NewOsFs(),
	})

	if err := run(ctx, os.Args); err != nil {
		os.Exit(1)
	}
}

// run launches the DC/OS CLI with a given context and args.
func run(ctx api.Context, args []string) error {
	var verbosity int
	var showVersion bool

	// Register the version and verbose global flags.
	// We ContinueOnError because we don't want to fail for subcommand specific flags.
	// We discard any output because we don't want the `-h` flag to trigger usage on this flagset.
	globalFlags := pflag.NewFlagSet(args[0], pflag.ContinueOnError)
	globalFlags.SetOutput(ioutil.Discard)
	globalFlags.BoolVar(&showVersion, "version", false, "")
	globalFlags.CountVarP(&verbosity, "", "v", "")
	globalFlags.Parse(args[1:])

	ctx.Logger().SetLevel(logLevel(verbosity))

	if showVersion {
		printVersion(ctx)
		return nil
	}
	return cmd.NewDCOSCommand(ctx).Execute()
}

// logLevel returns the log level for the CLI based on the verbosity. The default verbosity is 0.
func logLevel(verbosity int) logrus.Level {
	switch verbosity {
	case 0:
		// Without the verbose flag, default to error level.
		return logrus.ErrorLevel
	case 1:
		// -v sets the logger level to info.
		return logrus.InfoLevel
	default:
		// -vv sets the logger level to debug. This also happens for -vvv
		// and above, in such cases we set the logging level to its maximum.
		return logrus.DebugLevel
	}
}

// printVersion prints CLI version information.
func printVersion(ctx api.Context) {
	fmt.Fprintln(ctx.Out(), "dcoscli.version="+version)

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
