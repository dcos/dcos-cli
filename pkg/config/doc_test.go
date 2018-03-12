package config_test

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/config"
)

func ExampleNew() {
	conf := config.New()

	// Set the DC/OS URL and ACS token.
	conf.SetURL("https://dcos.example.com")
	conf.SetACSToken("token_ABC")

	// Set a path for the config and save it.
	conf.SetPath("/path/to/config.toml")
	err := conf.Save()
	if err != nil {
		// Handle error.
	}
}

func ExampleFromPath() {
	conf, err := config.FromPath("/path/to/config.toml")
	if err != nil {
		// Handle error.
	}

	// Displays the DC/OS URL if it exists in the file.
	fmt.Println(conf.URL())

	// Change the cluster name.
	conf.SetClusterName("my-new-cluster-name")

	// Save the config file.
	err = conf.Save()
	if err != nil {
		// Handle error.
	}
}

func ExampleFromString() {
	conf, err := config.FromString(`
[core]

dcos_url = "https://example.com"
dcos_acs_token = "token_zj8Tb0vhQw"
ssl_verify = "/path/to/dcos_ca.crt"

[cluster]
name = "my-cluster"
`)
	if err != nil {
		// Handle error.
	}

	fmt.Println(conf.URL())         // https://example.com
	fmt.Println(conf.ACSToken())    // "token_zj8Tb0vhQw"
	fmt.Println(conf.ClusterName()) // "my-cluster"
}
