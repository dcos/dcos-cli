package login

import (
	"encoding/json"

	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
)

// Client is able to detect available login providers and login to DC/OS.
type Client struct {
	http   *httpclient.Client
	logger *logrus.Logger
}

// NewClient creates a new login client.
func NewClient(baseClient *httpclient.Client, logger *logrus.Logger) *Client {
	return &Client{
		http:   baseClient,
		logger: logger,
	}
}

// Providers returns the supported login providers for a given DC/OS cluster.
func (c *Client) Providers() (map[string]*Provider, error) {
	resp, err := c.http.Get("/acs/api/v1/auth/providers")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var providers map[string]*Provider
	err = json.NewDecoder(resp.Body).Decode(&providers)
	return providers, err
}
