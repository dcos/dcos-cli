package main

import (
	"fmt"
	"os"
	"os/user"
	"time"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cmd"
	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/spf13/afero"
)

var version = "SNAPSHOT"

func main() {
	ctx := cli.NewContext(&cli.Environment{
		Args:       os.Args,
		Input:      os.Stdin,
		Out:        os.Stdout,
		ErrOut:     os.Stderr,
		EnvLookup:  os.LookupEnv,
		UserLookup: user.Current,
		Fs:         afero.NewOsFs(),
	})

	if len(os.Args) == 2 && os.Args[1] == "--version" {
		printVersion(ctx)
		return
	}

	if err := cmd.NewDCOSCommand(ctx).Execute(); err != nil {
		os.Exit(1)
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
