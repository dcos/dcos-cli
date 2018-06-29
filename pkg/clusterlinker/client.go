package clusterlinker

import (
	"bytes"
	"encoding/json"
	"errors"

	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
)

// Client is able to detect available login providers and login to DC/OS.
type Client struct {
	http   *httpclient.Client
	logger *logrus.Logger
}

// Link is the request sent to the /v1/links endpoint to link the cluster
// handled by the client to a cluster using its id, name, url, and login provider.
type Link struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	URL           string `json:"url"`
	LoginProvider `json:"login_provider"`
}

// LoginProvider representing a part of the message when sending a link request,
// it gives information about the cluster to link to.
type LoginProvider struct {
	ID   string `json:"id"`
	Type string `json:"type"`
}

type links struct {
	Links []*Link `json:"links"`
}

// NewClient creates a new cluster linker client from a standard HTTP client.
func NewClient(baseClient *httpclient.Client, logger *logrus.Logger) *Client {
	return &Client{
		http:   baseClient,
		logger: logger,
	}
}

// Link sends a link request to /v1/links using a given client.
func (c *Client) Link(linkRequest *Link) error {
	message, err := json.Marshal(linkRequest)

	resp, err := c.http.Post("/cluster/v1/links", "application/json", bytes.NewReader(message))
	if err != nil {
		return err
	}

	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		// links is a new endpoint, if it is not available DC/OS will not return an API error.
		if resp.StatusCode == 404 {
			return errors.New("inaccessible endpoint, cannot link cluster")
		}

		var apiError *dcos.Error
		if err := json.NewDecoder(resp.Body).Decode(&apiError); err != nil {
			return err
		}
		return apiError
	}

	return nil
}

// Unlink sends an unlink request to /v1/links using a given client.
func (c *Client) Unlink(linkedClusterID string) error {
	resp, err := c.http.Delete("/cluster/v1/links/" + linkedClusterID)
	if err != nil {
		return err
	}

	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		var apiError *dcos.Error
		if err := json.NewDecoder(resp.Body).Decode(&apiError); err != nil {
			return errors.New("couldn't unlink")
		}
		return apiError
	}

	return nil
}

// Links returns the links of a cluster.
func (c *Client) Links() ([]*Link, error) {
	resp, err := c.http.Get("/cluster/v1/links")
	if err != nil {
		return nil, errors.New("couldn't get linked clusters")
	}

	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		// links is a new endpoint, if it is not available DC/OS will not return an API error.
		if resp.StatusCode == 404 {
			return nil, errors.New("inaccessible endpoint, cannot find linked clusters")
		}

		var apiError *dcos.Error
		if err := json.NewDecoder(resp.Body).Decode(&apiError); err != nil {
			return nil, err
		}
		return nil, apiError
	}

	links := &links{}
	err = json.NewDecoder(resp.Body).Decode(&links)
	if err != nil {
		return nil, err
	}
	return links.Links, nil
}
