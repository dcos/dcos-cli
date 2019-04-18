package cosmos

import (
	"fmt"
	"net/url"
	"runtime"

	"github.com/dcos/client-go/dcos"
)

// NewClient creates a new Cosmos client.
func NewClient() (*dcos.CosmosApiService, error) {
	dcosClient, err := dcos.NewClient()
	if err != nil {
		return nil, err
	}
	return dcosClient.Cosmos, nil
}

// CLIPluginInfo extracts plugin resource data from the Cosmos package and for the current platform.
func CLIPluginInfo(pkg dcos.CosmosPackageDescribeV3Response, baseURL *url.URL) (cliArtifact dcos.CosmosPackageResourceCliArtifact, err error) {
	switch runtime.GOOS {
	case "linux":
		cliArtifact = pkg.Package.Resource.Cli.Binaries.Linux.X8664
	case "darwin":
		cliArtifact = pkg.Package.Resource.Cli.Binaries.Darwin.X8664
	case "windows":
		cliArtifact = pkg.Package.Resource.Cli.Binaries.Windows.X8664

	}
	// Workaround for a Cosmos bug leading to wrong schemes in plugin resource URLs.
	// This happens on setups with TLS termination proxies, where Cosmos might rewrite
	// the scheme to HTTP while it is actually HTTPS. The other way around is also possible.
	// See https://jira.mesosphere.com/browse/COPS-3052 for more context.
	//
	// To prevent this we're rewriting such URLs with the scheme set in `core.dcos_url`.
	pluginURL, err := url.Parse(cliArtifact.Url)
	if err != nil {
		return cliArtifact, err
	}
	if pluginURL.Hostname() == baseURL.Hostname() {
		pluginURL.Scheme = baseURL.Scheme
		cliArtifact.Url = pluginURL.String()
	}
	if cliArtifact.Url == "" {
		err = fmt.Errorf("'%s' isn't available for '%s')", pkg.Package.Name, runtime.GOOS)
	}
	return cliArtifact, err
}
