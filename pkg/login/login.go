package login

import (
	"bytes"
	"encoding/json"
	"fmt"

	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
)

// Credentials is the payload for login POST requests.
type Credentials struct {
	UID      string `json:"uid"`
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
		return providers, nil
	}

	c.logger.Info("Falling back to the WWW-Authenticate challenge.")

	// This is for DC/OS EE 1.7/1.8 and DC/OS Open Source.
	authHeader, err := c.challengeAuth()
	if err != nil {
		return nil, err
	}

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
	req, err := c.http.NewRequest("HEAD", "/pkgpanda/active.buildinfo.full.json", nil)
	if err != nil {
		return "", err
	}
	req.Header.Del("Authorization")

	resp, err := c.http.Do(req)
	if err != nil {
		return "", err
	}
	resp.Body.Close()

	if resp.StatusCode != 401 {
		return "", fmt.Errorf("expected status code 401, got %d", resp.StatusCode)
	}
	return resp.Header.Get("WWW-Authenticate"), nil
}

// Login makes a POST requests to the login endpoint with the given credentials.
func (c *Client) Login(loginEndpoint string, credentials *Credentials) (string, error) {
	if loginEndpoint == "" {
		loginEndpoint = "/acs/api/v1/auth/login"
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
