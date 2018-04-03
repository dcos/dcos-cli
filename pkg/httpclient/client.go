package httpclient

import (
	"context"
	"io"
	"net"
	"net/http"
	"time"
)

// A Client is an HTTP client.
type Client struct {
	acsToken   string
	baseURL    string
	timeout    time.Duration
	baseClient *http.Client
}

// Option is a functional option for an HTTP client.
type Option func(*Client)

// RequestOption is a functional option for an HTTP request.
type RequestOption func(*http.Request)

// reqContextKey is used to set values in request contexts.
type reqContextKey int

const (
	// keyNoTimeout is a context key indicating that no timeout should be set for a given request.
	keyNoTimeout reqContextKey = iota
)

// New returns a new HTTP client for a given baseURL and functional options.
func New(baseURL string, opts ...Option) *Client {
	client := &Client{
		baseURL: baseURL,
		baseClient: &http.Client{
			Transport: &http.Transport{

				// Allow http_proxy, https_proxy, and no_proxy.
				Proxy: http.ProxyFromEnvironment,

				// Set a 10 seconds timeout for the connection to be established.
				DialContext: (&net.Dialer{
					Timeout: 10 * time.Second,
				}).DialContext,

				// Set it to 10 seconds as well for the TLS handshake when using HTTPS.
				TLSHandshakeTimeout: 10 * time.Second,

				// The client will be dealing with a single host (the one in baseURL),
				// set max idle connections to 30 regardless of the host.
				MaxIdleConns:        30,
				MaxIdleConnsPerHost: 30,
			},
		},

		// Default request timeout to 3 minutes. We don't use http.Client.Timeout on purpose as the
		// current approach allows to change the timeout on a per-request basis. The same client can
		// be shared for requests with different timeouts.
		timeout: 3 * time.Minute,
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

// NoTimeout disables the timeout for an HTTP request.
func NoTimeout() RequestOption {
	return func(req *http.Request) {
		ctx := context.WithValue(req.Context(), keyNoTimeout, struct{}{})
		*req = *req.WithContext(ctx)
	}
}

// NewRequest returns a new Request given a method, path, and optional body.
// Also adds the authorization header with the ACS token to work with the
// DC/OS cluster we are linked to if it has been set.
func (c *Client) NewRequest(method, path string, body io.Reader, opts ...RequestOption) (*http.Request, error) {
	req, err := http.NewRequest(method, c.baseURL+path, body)
	if err != nil {
		return nil, err
	}

	if c.acsToken != "" {
		req.Header.Add("Authorization", "token="+c.acsToken)
	}

	for _, opt := range opts {
		opt(req)
	}

	if c.timeout > 0 {
		ctx := req.Context()
		noTimeout := ctx.Value(keyNoTimeout)

		if noTimeout == nil {
			newCtx, cancel := context.WithTimeout(ctx, c.timeout)
			go func() {
				<-ctx.Done()
				cancel()
			}()
			req = req.WithContext(newCtx)
		}
	}
	return req, nil
}

// Do sends an HTTP request and returns an HTTP response, following
// policy (such as redirects, cookies, auth) as configured on the
// client.
func (c *Client) Do(req *http.Request) (*http.Response, error) {
	return c.baseClient.Do(req)
}
