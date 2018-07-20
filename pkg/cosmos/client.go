package cosmos

import (
	"bytes"
	"encoding/json"
	"net/url"

	"github.com/dcos/dcos-cli/pkg/httpclient"
)

// Client is a client for Cosmos.
type Client struct {
	http *httpclient.Client
}

// NewClient creates a new Cosmos client.
func NewClient(baseClient *httpclient.Client) *Client {
	return &Client{
		http: baseClient,
	}
}

// PackageInfo contains information about a DC/OS package.
// It is mirroring the JSON response of the `/package/describe`
// endpoint for unmarshalling convenience.
type PackageInfo struct {
	Package struct {
		PackagingVersion      string `json:"packagingVersion"`
		Name                  string `json:"name"`
		Description           string `json:"description"`
		Version               string `json:"version"`
		ReleaseVersion        int    `json:"releaseVersion"`
		MinDCOSReleaseVersion string `json:"minDcosReleaseVersion"`
		Framework             bool   `json:"framework"`
		Maintainer            string `json:"maintainer"`
		Resource              struct {
			CLI struct {
				Plugins map[string]map[string]*Plugin `json:"binaries"`
			} `json:"cli"`
		} `json:"resource"`
	} `json:"package"`
}

// Plugin represents a CLI plugin resource.
type Plugin struct {
	Kind string `json:"kind"`
	URL  string `json:"url"`
}

// DescribePackage returns information about the named package.
func (c *Client) DescribePackage(name string) (*PackageInfo, error) {
	reqBodyPayload := map[string]string{"packageName": name}

	var reqBody bytes.Buffer
	if err := json.NewEncoder(&reqBody).Encode(reqBodyPayload); err != nil {
		return nil, err
	}

	req, err := c.http.NewRequest("POST", "/package/describe", &reqBody, httpclient.FailOnErrStatus(true))
	if err != nil {
		return nil, err
	}
	req.Header.Set(
		"Content-Type",
		"application/vnd.dcos.package.describe-request+json;charset=utf-8;version=v1",
	)
	req.Header.Set(
		"Accept",
		"application/vnd.dcos.package.describe-response+json;charset=utf-8;version=v3",
	)
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}

	defer resp.Body.Close()

	var pkg PackageInfo
	err = json.NewDecoder(resp.Body).Decode(&pkg)
	if err != nil {
		return nil, err
	}

	// Workaround for a Cosmos bug leading to wrong schemes in plugin resource URLs.
	// This happens on setups with TLS termination proxies, where Cosmos might rewrite
	// the scheme to HTTP while it is actually HTTPS. The other way around is also possible.
	// See https://jira.mesosphere.com/browse/COPS-3052 for more context.
	//
	// To prevent this we're rewriting such URLs with the scheme set in `core.dcos_url`.
	httpClientBaseURL := c.http.BaseURL()
	for _, plugins := range pkg.Package.Resource.CLI.Plugins {
		for _, plugin := range plugins {
			pluginURL, err := url.Parse(plugin.URL)
			if err != nil {
				continue
			}
			if pluginURL.Hostname() == httpClientBaseURL.Hostname() {
				pluginURL.Scheme = httpClientBaseURL.Scheme
				plugin.URL = pluginURL.String()
			}
		}
	}
	return &pkg, err
}
