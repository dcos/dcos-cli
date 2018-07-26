package httpclient

import (
	"context"
	"crypto/tls"
	"io"
	"net"
	"net/http"
	"net/http/httputil"
	"time"

	"github.com/sirupsen/logrus"
)

// A Client is an HTTP client.
type Client struct {
	baseURL    string
	baseClient *http.Client
	opts       Options
}

// Option is a functional option for an HTTP client.
type Option func(opts *Options)

// Options are configuration options for an HTTP client.
type Options struct {
	Timeout       time.Duration
	TLS           *tls.Config
	Logger        *logrus.Logger
	ACSToken      string
	CheckRedirect func(req *http.Request, via []*http.Request) error
}

// TLS sets the TLS configuration for the HTTP client transport.
func TLS(tlsConfig *tls.Config) Option {
	return func(opts *Options) {
		opts.TLS = tlsConfig
	}
}

// ACSToken sets the authentication token for HTTP requests.
func ACSToken(token string) Option {
	return func(opts *Options) {
		opts.ACSToken = token
	}
}

// Timeout sets the timeout for HTTP requests.
func Timeout(timeout time.Duration) Option {
	return func(opts *Options) {
		opts.Timeout = timeout
	}
}

// Logger sets the logger for the HTTP client.
func Logger(logger *logrus.Logger) Option {
	return func(opts *Options) {
		opts.Logger = logger
	}
}

// NoFollow prevents the client to follow redirect responses.
func NoFollow() Option {
	return func(opts *Options) {
		noFollow := func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		}
		opts.CheckRedirect = noFollow
	}
}

// New returns a new HTTP client for a given baseURL and functional options.
func New(baseURL string, opts ...Option) *Client {
	// Default request timeout to 3 minutes. We don't use http.Client.Timeout on purpose as the
	// current approach allows to change the timeout on a per-request basis. The same client can
	// be shared for requests with different timeouts.
	options := Options{Timeout: 3 * time.Minute}

	for _, opt := range opts {
		opt(&options)
	}

	return &Client{
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

				// Set the TLS configuration as specified in the context.
				TLSClientConfig: options.TLS,
			},

			// Specify the redirect policy for the client.
			CheckRedirect: options.CheckRedirect,
		},
		opts: options,
	}
}

// Get issues a GET to the specified DC/OS cluster path.
func (c *Client) Get(path string, opts ...Option) (*http.Response, error) {
	req, err := c.NewRequest("GET", path, nil, opts...)
	if err != nil {
		return nil, err
	}
	return c.Do(req)
}

// Post issues a POST to the specified DC/OS cluster path.
func (c *Client) Post(path string, contentType string, body io.Reader, opts ...Option) (*http.Response, error) {
	req, err := c.NewRequest("POST", path, body, opts...)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", contentType)
	return c.Do(req)
}

// Delete issues a DELETE to the specified DC/OS cluster path.
func (c *Client) Delete(path string, opts ...Option) (*http.Response, error) {
	req, err := c.NewRequest("DELETE", path, nil, opts...)
	if err != nil {
		return nil, err
	}
	return c.Do(req)
}

// NewRequest returns a new Request given a method, path, and optional body.
// Also adds the authorization header with the ACS token to work with the
// DC/OS cluster we are linked to if it has been set.
func (c *Client) NewRequest(method, path string, body io.Reader, opts ...Option) (*http.Request, error) {
	req, err := http.NewRequest(method, c.baseURL+path, body)
	if err != nil {
		return nil, err
	}

	options := c.opts
	for _, opt := range opts {
		opt(&options)
	}

	if options.ACSToken != "" {
		req.Header.Add("Authorization", "token="+options.ACSToken)
	}

	if options.Timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel := context.WithTimeout(req.Context(), options.Timeout)
		go func() {
			<-ctx.Done()
			cancel()
		}()
		req = req.WithContext(ctx)
	}
	return req, nil
}

// Do sends an HTTP request and returns an HTTP response, following
// policy (such as redirects, cookies, auth) as configured on the
// client.
func (c *Client) Do(req *http.Request) (*http.Response, error) {
	logger := c.opts.Logger

	if logger != nil && logger.Level >= logrus.DebugLevel {
		reqDump, err := httputil.DumpRequestOut(req, true)
		if err != nil {
			logger.Debug("Couldn't dump request: %s", err)
		} else {
			logger.Debug(string(reqDump))
		}
	}

	resp, err := c.baseClient.Do(req)

	if logger != nil && logger.Level >= logrus.DebugLevel {
		if err == nil {
			respDump, err := httputil.DumpResponse(resp, true)
			if err != nil {
				logger.Debug("Couldn't dump response: %s", err)
			} else {
				logger.Debug(string(respDump))
			}
		} else {
			logger.Debug(err)
		}
	}
	return resp, err
}
