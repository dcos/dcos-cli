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

	// In the case of autocomplete the first 3 args will always be `dcos __autocomplete__ dcos`
	if len(args) >= 3 && args[1] == "__autocomplete__" {
		autocomplete := cmdTree.AutocompleteCommand(ctx)

		// We want to ignore the `dcos __autocomplete__` since that's not part of the autocomplete tree
		// and we need to take off the second `dcos` because that's what cobra normally does when you haven't
		// overriden Command::Args but since we do here, we need to take it off manually.
		autocomplete.SetArgs(args[3:])

		if err := autocomplete.Execute(); err != nil {
			os.Exit(1)
		}
	} else {
		if err := cmdTree.RunCommand().Execute(); err != nil {
			os.Exit(1)
		}
	}
}
