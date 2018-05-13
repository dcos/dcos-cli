package mesos

import (
	"encoding/json"

	"github.com/dcos/dcos-cli/pkg/httpclient"
)

// Client is a Mesos client for DC/OS.
type Client struct {
	http *httpclient.Client
}

// NewClient creates a new Mesos client.
func NewClient(baseClient *httpclient.Client) *Client {
	return &Client{
		http: baseClient,
	}
}

// StateSummary contains a summary of agents, tasks, and registered frameworks in the DC/OS cluster.
type StateSummary struct {
	Cluster string `json:"cluster"`
}

// StateSummary returns the `/state/summary` from the Mesos master.
func (c *Client) StateSummary() (*StateSummary, error) {
	resp, err := c.http.Get("/mesos/state-summary")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var stateSummary StateSummary
	err = json.NewDecoder(resp.Body).Decode(&stateSummary)
	return &stateSummary, err
}
