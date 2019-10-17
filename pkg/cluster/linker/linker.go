package linker

import (
	"bytes"
	"encoding/json"
	"errors"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
)

// Linker manages DC/OS cluster links.
type Linker struct {
	http   *httpclient.Client
	logger *logrus.Logger
}

// Link is the request sent to the /cluster/v1/links endpoint to link the cluster
// handled by the client to a cluster using its id, name, url, and login provider.
type Link struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	URL           string `json:"url"`
	LoginProvider `json:"login_provider"`
}

// ToCluster converts a link to a config.Cluster.
func (l *Link) ToCluster() *config.Cluster {
	cluster := config.NewCluster(nil)
	cluster.SetID(l.ID)
	cluster.SetName(l.Name)
	cluster.SetURL(l.URL)
	return cluster
}

// LoginProvider representing a part of the message when sending a link request,
// it gives information about the cluster to link to.
type LoginProvider struct {
	ID   string `json:"id"`
	Type string `json:"type"`
}

// Links is the structure returned by the /cluster/v1/links endpoint.
type Links struct {
	Links []*Link `json:"links"`
}

// New creates a new cluster linker client from a standard HTTP client.
func New(baseClient *httpclient.Client, logger *logrus.Logger) *Linker {
	return &Linker{
		http:   baseClient,
		logger: logger,
	}
}

// Link sends a link request to /cluster/v1/links using a given client.
func (l *Linker) Link(link *Link) error {
	message, err := json.Marshal(link)
	if err != nil {
		return err
	}

	l.logger.Info("Linking the cluster...")
	resp, err := l.http.Post(
		"/cluster/v1/links",
		"application/json",
		bytes.NewReader(message),
		httpclient.FailOnErrStatus(false),
	)
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

	l.logger.Infof("Linked current cluster to cluster %s", link.ID)
	return nil
}

// Unlink sends an unlink request to /cluster/v1/links.
func (l *Linker) Unlink(id string) error {
	l.logger.Info("Unlinking the cluster...")
	resp, err := l.http.Delete("/cluster/v1/links/"+id, httpclient.FailOnErrStatus(false))
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

	l.logger.Infof("Unlinked current cluster from cluster %s", id)
	return nil
}

// Links returns the links of a cluster.
func (l *Linker) Links() ([]*Link, error) {
	resp, err := l.http.Get("/cluster/v1/links", httpclient.FailOnErrStatus(false))
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

	links := &Links{}
	err = json.NewDecoder(resp.Body).Decode(&links)
	if err != nil {
		return nil, err
	}
	return links.Links, nil
}
