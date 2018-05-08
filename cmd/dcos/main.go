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

	args := os.Args
	cmdTree := cmd.NewDcosSubCommand(ctx)

	if len(args) > 1 && args[1] == "__autocomplete__" {
		autocomplete := cmdTree.AutocompleteCommand(ctx)

		// we chop off the first 2 args which will be `dcos __autocomplete__` to let the autocomplete tree
		// start from the actual command being completed
		autocomplete.SetArgs(args[2:])

		if err := autocomplete.Execute(); err != nil {
			os.Exit(1)
		}
	} else {
		if err := cmdTree.RunCommand().Execute(); err != nil {
			os.Exit(1)
		}
	}
}
