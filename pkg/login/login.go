package login

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"

	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
)

const defaultLoginEndpoint = "/acs/api/v1/auth/login"

var (
	// ErrAuthDisabled is the error returned when attempting to get authentication providers
	// from a cluster without authentication.
	ErrAuthDisabled = errors.New("authentication disabled")
)

// Credentials is the payload for login POST requests.
type Credentials struct {
	UID      string `json:"uid,omitempty"`
	Password string `json:"password,omitempty"`
	Token    string `json:"token,omitempty"`
}

// JWT is the authentication token returned by the DC/OS login API.
type JWT struct {
	Token string `json:"token"`
}

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
func (c *Client) Providers() (Providers, error) {
	authHeader, err := c.challengeAuth()
	if err != nil {
		return nil, err
	}

	resp, err := c.http.Get("/acs/api/v1/auth/providers")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	providers := Providers{}
	if resp.StatusCode == 200 {
		err := json.NewDecoder(resp.Body).Decode(&providers)
		if err != nil {
			return nil, err
		}

		if authHeader == "oauthjwt" {
			// DC/OS Open Source >= 1.13.
			provider := defaultOIDCImplicitFlowProvider()
			providers[provider.ID] = provider
		}
		return providers, nil
	}

	// This is for DC/OS EE 1.7/1.8 and DC/OS Open Source < 1.13.
	c.logger.Info("Falling back to the WWW-Authenticate challenge.")
	switch authHeader {
	case "oauthjwt":
		// DC/OS Open Source
		provider := defaultOIDCImplicitFlowProvider()
		providers[provider.ID] = provider
	case "acsjwt":
		// DC/OS EE 1.7/1.8
		provider := defaultDCOSUIDPasswordProvider()
		providers[provider.ID] = provider
	default:
		return nil, fmt.Errorf("unsupported WWW-Authenticate challenge '%s'", authHeader)
	}
	return providers, nil
}

// challengeAuth sends an unauthenticated HTTP request to a DC/OS well-known resource.
// It then expects a 401 response with a WWW-Authenticate header containing the login method to use.
// This method is used to determine which login provider is available when the /acs/api/v1/auth/providers
// endpoint is not present.
func (c *Client) challengeAuth() (string, error) {
	resp, err := c.sniffAuth("")
	if err != nil {
		return "", err
	}

	switch resp.StatusCode {
	case 200:
		return "", ErrAuthDisabled
	case 401:
		return resp.Header.Get("WWW-Authenticate"), nil
	default:
		return "", fmt.Errorf("expected status code 401, got %d", resp.StatusCode)
	}
}

// sniffAuth sends an HTTP request with a given ACS token to a well-known resource.
// It is mainly used to challenge auth or verify that an ACS token is valid.
func (c *Client) sniffAuth(acsToken string) (*http.Response, error) {
	opts := []httpclient.Option{
		httpclient.FailOnErrStatus(false),
	}
	if acsToken != "" {
		opts = append(opts, httpclient.ACSToken(acsToken))
	}
	req, err := c.http.NewRequest("HEAD", "/pkgpanda/active.buildinfo.full.json", nil, opts...)
	if err != nil {
		return nil, err
	}
	if acsToken == "" {
		// When an empty ACS token is passed, we're challenging auth.
		// Make sure the Authorization header is empty.
		delete(req.Header, "Authorization")
	}
	return c.http.Do(req)
}

// Login makes a POST requests to the login endpoint with the given credentials.
func (c *Client) Login(loginEndpoint string, credentials *Credentials) (string, error) {
	if loginEndpoint == "" {
		loginEndpoint = defaultLoginEndpoint
	}

	reqBody, err := json.Marshal(credentials)
	if err != nil {
		return "", err
	}

	resp, err := c.http.Post(loginEndpoint, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		var apiError *dcos.Error
		if err := json.NewDecoder(resp.Body).Decode(&apiError); err != nil {
			return "", fmt.Errorf("couldn't log in")
		}
		return "", apiError
	}

	var jwt *JWT
	if err := json.NewDecoder(resp.Body).Decode(&jwt); err != nil {
		return "", err
	}
	return jwt.Token, nil
}
