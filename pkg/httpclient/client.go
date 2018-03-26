package httpclient

import (
	"io"
	"net/http"
)

// A Client is an HTTP client.
type Client struct {
	acsToken   string
	baseURL    string
	baseClient *http.Client
}

// Option is a functional option for an HTTP client.
type Option func(*Client)

// New returns a new HTTP client for a given baseURL and functional options.
func New(baseURL string, opts ...Option) *Client {
	client := &Client{
		baseURL:    baseURL,
		baseClient: &http.Client{},
	}
	for _, opt := range opts {
		opt(client)
	}
	return client
}

// Get issues a GET to the specified DC/OS cluster path.
func (c *Client) Get(path string) (*http.Response, error) {
	req, err := c.NewRequest("GET", path, nil)
	if err != nil {
		return nil, err
	}
	return c.Do(req)
}

// Post issues a POST to the specified DC/OS cluster path.
func (c *Client) Post(path string, contentType string, body io.Reader) (*http.Response, error) {
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
func (c *Client) NewRequest(method, path string, body io.Reader) (*http.Request, error) {
	req, err := http.NewRequest(method, c.baseURL+path, body)
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
func (c *Client) Do(req *http.Request) (*http.Response, error) {
	return c.baseClient.Do(req)
}
