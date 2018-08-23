package httpclient

//go:generate goderive

import (
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"mime"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"runtime"
	"strings"
	"time"

	"github.com/dcos/dcos-cli/pkg/cli/version"
	"github.com/sirupsen/logrus"
)

// defaultUserAgent for HTTP requests (eg. "dcos-cli/0.7.1 linux").
var defaultUserAgent = fmt.Sprintf("dcos-cli/%s %s", version.Version(), runtime.GOOS)

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
	Header          http.Header
	Timeout         time.Duration
	TLS             *tls.Config
	Logger          *logrus.Logger
	CheckRedirect   func(req *http.Request, via []*http.Request) error
	FailOnErrStatus bool
}

// ctxKey is a custom type to set values in request contexts.
type ctxKey int

// ctxKeyFailOnErrStatus is a request context key which, when sets, indicates that
// the HTTP client should return in error when it encounters an HTTP error (4XX / 5XX).
const ctxKeyFailOnErrStatus ctxKey = 0

// TLS sets the TLS configuration for the HTTP client transport.
func TLS(tlsConfig *tls.Config) Option {
	return func(opts *Options) {
		opts.TLS = tlsConfig
	}
}

// ACSToken sets the authentication token for HTTP requests.
func ACSToken(token string) Option {
	return Header("Authorization", "token="+token)
}

// Header sets an HTTP header.
func Header(key, value string) Option {
	return func(opts *Options) {
		opts.Header.Set(key, value)
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

// FailOnErrStatus specifies whether or not the client should fail on HTTP error response (4XX / 5XX).
func FailOnErrStatus(failOnErrStatus bool) Option {
	return func(opts *Options) {
		opts.FailOnErrStatus = failOnErrStatus
	}
}

// New returns a new HTTP client for a given baseURL and functional options.
func New(baseURL string, opts ...Option) *Client {
	options := Options{
		Header: make(http.Header),

		// Default request timeout to 3 minutes. We don't use http.Client.Timeout on purpose as the
		// current approach allows to change the timeout on a per-request basis. The same client can
		// be shared for requests with different timeouts.
		Timeout: 3 * time.Minute,
	}

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
	options.Header = make(http.Header)
	deriveDeepCopy(options.Header, c.opts.Header)
	for _, opt := range opts {
		opt(&options)
	}

	req.Header = options.Header

	// Set the default User-Agent unless the header is already set.
	if _, ok := req.Header["User-Agent"]; !ok {
		req.Header.Set("User-Agent", defaultUserAgent)
	}

	if options.FailOnErrStatus {
		ctx := context.WithValue(req.Context(), ctxKeyFailOnErrStatus, struct{}{})
		req = req.WithContext(ctx)
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
		dumpBody := c.isText(req.Header.Get("Content-Type"))
		reqDump, err := httputil.DumpRequestOut(req, dumpBody)
		if err != nil {
			logger.Debugf("Couldn't dump request: %s", err)
		} else {
			logger.Debug(string(reqDump))
		}
	}

	resp, err := c.baseClient.Do(req)

	if logger != nil && logger.Level >= logrus.DebugLevel {
		if err == nil {
			dumpBody := c.isText(resp.Header.Get("Content-Type"))
			respDump, err := httputil.DumpResponse(resp, dumpBody)
			if err != nil {
				logger.Debugf("Couldn't dump response: %s", err)
			} else {
				logger.Debug(string(respDump))
			}
		} else {
			logger.Debug(err)
		}
	}

	if err == nil {
		_, failOnErrStatus := req.Context().Value(ctxKeyFailOnErrStatus).(struct{})

		if failOnErrStatus && resp.StatusCode >= 400 && resp.StatusCode < 600 {
			return nil, fmt.Errorf("HTTP %d error", resp.StatusCode)
		}
	}
	return resp, err
}

// BaseURL returns the HTTP client's base URL.
func (c *Client) BaseURL() *url.URL {
	baseURL, err := url.Parse(c.baseURL)
	if err != nil && c.opts.Logger != nil {
		// We don't return error-out to keep the method signature clean.
		// If an http client contains an invalid URL it is broken anyway and
		// it is not this method responsibility to check this.
		c.opts.Logger.Debug(err)
	}
	return baseURL
}

// isText returns whether the Content-type header refers to a textual body.
func (c *Client) isText(contentType string) bool {
	mediaType, _, err := mime.ParseMediaType(contentType)
	if err != nil {
		c.opts.Logger.Debug(err)
		return false
	}
	if mediaType == "application/json" || strings.HasSuffix(mediaType, "+json") {
		return true
	}
	return strings.HasPrefix(mediaType, "text/")
}
