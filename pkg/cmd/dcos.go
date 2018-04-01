// Package cmd defines commands for the DC/OS CLI.
package cmd

import (
	"fmt"
	"io"
	"os"
	"os/user"
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/spf13/cobra"
)

// NewDCOSCommand creates the `dcos` command with its `auth`, `config`, and `cluster` subcommands.
func NewDCOSCommand(out, err io.Writer) *cobra.Command {
	cmd := &cobra.Command{
		Use: "dcos",
	}
	cmd.AddCommand(
		newCmdAuth(out, err),
		newCmdConfig(out, err),
		newCmdCluster(out, err),
	)
	return cmd
}

// Cluster is a temporary struct representing a cluster until we have the proper abstraction for this.
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

	// Default to the old config path. If .dcos/clusters exists, it will search that for an attached cluster and if it
	// finds one there, it will override this var to use that cluster's config instead.
	configPath := filepath.Join(usr.HomeDir, ".dcos")

	clustersDir := filepath.Join(configPath, "clusters")

	// Find the config of the attached cluster.
	err = filepath.Walk(clustersDir, func(path string, info os.FileInfo, err error) error {
		if filepath.Base(path) == "attached" {
			configPath = filepath.Dir(path)
			return io.EOF
		}
		return nil
	})
	if err != io.EOF && err != filepath.SkipDir && err != nil {
		fmt.Println(err)
	}


	// Make sure "~/.dcos/dcos.toml" exists.
	path := filepath.Join(configPath, "dcos.toml")
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
