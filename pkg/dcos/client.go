package dcos

import (
	"encoding/json"

	"github.com/dcos/dcos-cli/pkg/httpclient"
)

// Client is a generic client for DC/OS.
type Client struct {
	http *httpclient.Client
}

// NewClient creates a new DC/OS client.
func NewClient(baseClient *httpclient.Client) *Client {
	return &Client{
		http: baseClient,
	}
}

// Version contains information about the DC/OS version.
type Version struct {
	Version         string `json:"version"`
	DCOSVariant     string `json:"dcos-variant"`
	DCOSImageCommit string `json:"dcos-image-commit"`
	BootstrapID     string `json:"bootstrap-id"`
}

// Version returns the DC/OS version metadata from "/dcos-metadata/dcos-version.json".
func (c *Client) Version() (*Version, error) {
	resp, err := c.http.Get("/dcos-metadata/dcos-version.json")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var version Version
	err = json.NewDecoder(resp.Body).Decode(&version)
	return &version, err
}

// Metadata contains the DC/OS version metadata.
type Metadata struct {
	PublicIPv4 string `json:"PUBLIC_IPV4"`
	ClusterID  string `json:"CLUSTER_ID"`
}

// Metadata returns the DC/OS cluster metadata from "/metadata".
func (c *Client) Metadata() (*Metadata, error) {
	resp, err := c.http.Get("/metadata")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var metadata Metadata
	err = json.NewDecoder(resp.Body).Decode(&metadata)
	return &metadata, err
}
