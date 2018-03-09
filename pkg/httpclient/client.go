package httpclient

import (
	"crypto/tls"
	"io"
	"net/http"
	"strings"

	"github.com/dcos/dcos-cli/pkg/config"
)

// A Client is an HTTP client.
type Client struct {
	acsToken string
	baseURL  string
	client   *http.Client
}

// New returns a new HTTP client based on a Config.
func New(conf config.Config) *Client {
	tlsConfig := &tls.Config{
		InsecureSkipVerify: conf.TLS().Insecure,
		RootCAs:            conf.TLS().RootCAs,
	}
	transport := &http.Transport{
		TLSClientConfig: tlsConfig,
	}
	client := &http.Client{
		Transport: transport,
		Timeout:   conf.Timeout(),
	}

	baseURL := strings.Trim(conf.URL(), "/")

	return &Client{
		acsToken: conf.ACSToken(),
		baseURL:  baseURL,
		client:   client,
	}
}

// Get issues a GET to the specified DC/OS cluster path.
func (c *Client) Get(path string) (resp *http.Response, err error) {
	req, err := c.NewRequest("GET", path, nil)
	if err != nil {
		return nil, err
	}
	return c.Do(req)
}

// Post issues a POST to the specified DC/OS cluster path.
func (c *Client) Post(path string, contentType string, body io.Reader) (resp *http.Response, err error) {
	req, err := c.NewRequest("POST", path, body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", contentType)
	return c.Do(req)
}

// NewRequest returns a new Request given a method, path, and optional body.
// Also adds the authorization header with the ACS token to work with the
// DC/OS cluster we are linked to if it has been set.
func (c *Client) NewRequest(method, path string, body io.Reader) (req *http.Request, err error) {
	req, err = http.NewRequest(method, c.baseURL+path, body)
	if err != nil {
		return nil, err
	}

	if c.acsToken != "" {
		req.Header.Add("Authorization", "token="+c.acsToken)
	}
	return req, nil
}

// Do sends an HTTP request and returns an HTTP response, following
// policy (such as redirects, cookies, auth) as configured on the
// client.
func (c *Client) Do(req *http.Request) (resp *http.Response, err error) {
	return c.client.Do(req)
}
