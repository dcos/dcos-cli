package config_test

import (
	"fmt"
	"strings"

	"github.com/dcos/dcos-cli/pkg/config"
)

func ExampleConfig_LoadPath() {
	store := config.Empty()
	err := store.LoadPath("/path/to/config.toml")
	if err != nil {
		// Handle error.
	}

	// Displays the DC/OS URL if it exists in the file.
	fmt.Println(store.Get("core.dcos_url"))

	// Change the cluster name.
	store.Set("cluster.name", "my-new-cluster-name")
}

func ExampleConfig_LoadReader() {
	store := config.Empty()
	err := store.LoadReader(strings.NewReader(`
[core]

dcos_url = "https://example.com"
dcos_acs_token = "token_zj8Tb0vhQw"
ssl_verify = "/path/to/dcos_ca.crt"

[cluster]
name = "my-cluster"
`))
	if err != nil {
		// Handle error.
	}

	fmt.Println(store.Get("core.dcos_url"))       // https://example.com
	fmt.Println(store.Get("core.dcos_acs_token")) // "token_zj8Tb0vhQw"
	fmt.Println(store.Get("core.cluster_name"))   // "my-cluster"
}
