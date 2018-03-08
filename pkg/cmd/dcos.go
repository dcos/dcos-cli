// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"fmt"
	"os"
	"os/user"
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/spf13/cobra"
)

// rootCmd represents the base command when called without any subcommands.
var rootCmd = &cobra.Command{
	Use: "dcos",
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

type Cluster struct {
	Config config.Config
}

// This is a temporary function until we have the proper abstraction for this.
func attachedCluster() *Cluster {
	// Determine the current user.
	usr, err := user.Current()
	if err != nil {
		fmt.Printf("Couldn't determine current user: %s.\n", err)
		os.Exit(1)
	}

	// Create the "~/.dcos" directory.
	dir := filepath.Join(usr.HomeDir, ".dcos")
	if err := os.MkdirAll(dir, 0755); err != nil {
		fmt.Printf("Couldn't create \"%s\": %s.\n", dir, err)
		os.Exit(1)
	}

	// Make sure "~/.dcos/dcos.toml" exists.
	path := filepath.Join(dir, "dcos.toml")
	f, err := os.OpenFile(path, os.O_RDONLY|os.O_CREATE, 0600)
	if err != nil {
		fmt.Printf("Couldn't create config file \"%s\": %s.\n", path, err)
		os.Exit(1)
	}
	f.Close()

	conf, err := config.FromPath(path)
	if err != nil {
		fmt.Printf("Couldn't parse config from \"%s\": %s.\n", path, err)
		os.Exit(1)
	}
	return &Cluster{
		Config: conf,
	}
}
