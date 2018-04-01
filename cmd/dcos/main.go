package main

import (
	"os"

	"github.com/dcos/dcos-cli/pkg/cmd"
)

func main() {
	if err := cmd.NewDCOSCommand(os.Stdout, os.Stderr).Execute(); err != nil {
		os.Exit(1)
	}
}
