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

type LoginProvider struct {
	ID   string `json:"id"`
	Type string `json:"type"`
}

type LinkRequest struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	URL           string `json:"url"`
	LoginProvider `json:"login_provider"`
}

// NewClient creates a new DC/OS client.
func NewClient(baseClient *httpclient.Client, logger *logrus.Logger) *Client {
	return &Client{
		http:   baseClient,
		logger: logger,
	}
}

func (c *Client) Link(linkRequest *LinkRequest) error {
	message, err := json.Marshal(linkRequest)

	resp, err := c.http.Post("/cluster/v1/links", "application/json", bytes.NewReader(message))
	if err != nil {
		return err
	}

	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		var apiError *dcos.Error
		if err := json.NewDecoder(resp.Body).Decode(&apiError); err != nil {
			return errors.New("couldn't link")
		}
		return apiError
	}

	return nil
}

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
