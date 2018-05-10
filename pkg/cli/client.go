package cli

import (
	"encoding/json"

	"github.com/dcos/dcos-cli/pkg/httpclient"
)

// DCOSClient is a generic client for DC/OS.
type DCOSClient struct {
	http *httpclient.Client
}

// NewDCOSClient creates a new DC/OS client.
func NewDCOSClient(baseClient *httpclient.Client) *DCOSClient {
	return &DCOSClient{
		http: baseClient,
	}
}

// Version contains information about the DC/OS version.
type Version struct {
	Version         string `json:"version"`
	DCOSImageCommit string `json:"dcos-image-commit"`
	BootstrapID     string `json:"bootstrap-id"`
}

// Version returns the DC/OS version metadata from "/dcos-metadata/dcos-version.json".
func (c *DCOSClient) Version() (*Version, error) {
	resp, err := c.http.Get("/dcos-metadata/dcos-version.json")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var version Version
	err = json.NewDecoder(resp.Body).Decode(&version)
	return &version, err
}
