package config_test

import (
	"fmt"

	"github.com/dcos/dcos-cli/pkg/config"
)

func ExampleFromPath() {
	conf, err := config.FromPath("/path/to/config.toml")
	if err != nil {
		// Handle error.
	}

	// Displays the DC/OS URL if it exists in the file.
	fmt.Println(conf.URL)
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

	fmt.Println(conf.URL)         // https://example.com
	fmt.Println(conf.ACSToken)    // "token_zj8Tb0vhQw"
	fmt.Println(conf.ClusterName) // "my-cluster"
}
