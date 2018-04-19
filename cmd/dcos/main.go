package main

import (
	"os"
	"os/user"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cmd"
	"github.com/spf13/afero"
)

func main() {
	ctx := cli.NewContext(&cli.Environment{
		Out:        os.Stdout,
		ErrOut:     os.Stderr,
		EnvLookup:  os.LookupEnv,
		UserLookup: user.Current,
		Fs:         afero.NewOsFs(),
	})

	if err := cmd.NewDCOSCommand(ctx).Execute(); err != nil {
		os.Exit(1)
	}
}
