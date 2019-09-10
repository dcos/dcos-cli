package dcos

import (
	"crypto/tls"
	"fmt"
	"mime"
	"net"
	"net/http"
	"net/http/httputil"
	"os"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
)

const (
	// defaultTransportDialTimeout specifies the maximum amount of time
	// waiting for a connection to be established.
	defaultTransportDialTimeout = 10 * time.Second

	// defaultTransportTLSHandshakeTimeout specifies the maximum
	// amount of time waiting to wait for a TLS handshake.
	defaultTransportTLSHandshakeTimeout = 10 * time.Second

	// defaultTransportMaxIdleConns specifies the maximum number of idle connections.
	defaultTransportMaxIdleConns = 30
)

// DefaultTransport is a http.RoundTripper that adds authentication based on Config.
type DefaultTransport struct {
	Config    *Config
	Base      http.RoundTripper
	Logger    *logrus.Logger
	UserAgent string
}

func (t *DefaultTransport) base() http.RoundTripper {
	if t.Base != nil {
		return t.Base
	}
	return http.DefaultTransport
}

// RoundTrip authorizes requests to DC/OS by adding dcos_acs_token to Authorization header.
func (t *DefaultTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	// meet the requirements of RoundTripper and only modify a copy
	req2 := cloneRequest(req)
	req2.Header.Set("Authorization", fmt.Sprintf("token=%s", t.Config.ACSToken()))

	// Specify a custom User-Agent if any, otherwise fallback to "client-go({version})".
	userAgent := t.UserAgent
	if userAgent == "" {
		userAgent = fmt.Sprintf("%s(%s)", ClientName, Version)
	}
	req2.Header.Set("User-Agent", userAgent)

	if t.Logger != nil && t.Logger.Level >= logrus.DebugLevel {
		dumpBody := t.isText(req.Header.Get("Content-Type"))
		reqDump, err := httputil.DumpRequestOut(req2, dumpBody)
		if err != nil {
			t.Logger.Debugf("Couldn't dump request: %s", err)
		} else {
			t.Logger.Debug(string(reqDump))
		}
	}

	resp, err := t.base().RoundTrip(req2)

	if err == nil && t.Logger != nil && t.Logger.Level >= logrus.DebugLevel {
		dumpBody := t.isText(resp.Header.Get("Content-Type"))
		respDump, err := httputil.DumpResponse(resp, dumpBody)
		if err != nil {
			t.Logger.Debugf("Couldn't dump response: %s", err)
		} else {
			t.Logger.Debug(string(respDump))
		}
	}

	return resp, err
}

// isText returns whether the Content-type header refers to a textual body.
func (t *DefaultTransport) isText(contentType string) bool {
	mediaType, _, err := mime.ParseMediaType(contentType)
	if err != nil {
		t.Logger.Debug(err)
		return false
	}
	if mediaType == "application/json" || strings.HasSuffix(mediaType, "+json") {
		return true
	}
	return strings.HasPrefix(mediaType, "text/")
}

func cloneRequest(req *http.Request) *http.Request {
	req2 := new(http.Request)
	*req2 = *req

	// until now we only clone headers as we only modify those.
	req2.Header = make(http.Header, len(req.Header))
	for k, s := range req.Header {
		req2.Header[k] = append([]string(nil), s...)
	}

	return req2
}

// NewDefaultTransport returns a new HTTP transport for a given Config.
func NewDefaultTransport(config *Config) *DefaultTransport {
	baseTransport := &http.Transport{
		// Allow http_proxy, https_proxy, and no_proxy.
		Proxy: http.ProxyFromEnvironment,

		DialContext: (&net.Dialer{
			Timeout: defaultTransportDialTimeout,
		}).DialContext,

		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: config.TLS().Insecure,
			RootCAs:            config.TLS().RootCAs,
		},

		TLSHandshakeTimeout: defaultTransportTLSHandshakeTimeout,

		// As the client is dealing with a single host (the DC/OS master node),
		// set both MaxIdleConns and MaxIdleConnsPerHost to the same value.
		MaxIdleConns:        defaultTransportMaxIdleConns,
		MaxIdleConnsPerHost: defaultTransportMaxIdleConns,
	}

	logger := logrus.New()
	if os.Getenv("DCOS_DEBUG") != "" {
		logger.SetLevel(logrus.DebugLevel)
	}

	return &DefaultTransport{
		Config: config,
		Base:   baseTransport,
		Logger: logger,
	}
}

// NewHTTPClient provides a http.Client able to communicate to dcos in an authenticated way.
func NewHTTPClient(config *Config) *http.Client {
	return &http.Client{
		Transport: NewDefaultTransport(config),
	}
}

// AddTransportHTTPClient adds dcos.DefaultTransport to http.Client to add dcos authentication.
func AddTransportHTTPClient(client *http.Client, config *Config) *http.Client {
	transport := DefaultTransport{
		Config: config,
		Base:   client.Transport,
	}

	client.Transport = &transport

	return client
}
