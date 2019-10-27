package login

import (
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/login/loginserver"
	"github.com/dcos/dcos-cli/pkg/open"
	"github.com/dcos/dcos-cli/pkg/prompt"
	"github.com/dgrijalva/jwt-go"
	"github.com/sirupsen/logrus"
)

// FlowOpts are functional options for a Flow.
type FlowOpts struct {
	Errout io.Writer
	Prompt *prompt.Prompt
	Logger *logrus.Logger
	Opener open.Opener
}

// Flow represents a login flow.
type Flow struct {
	client      *Client
	errout      io.Writer
	prompt      *prompt.Prompt
	logger      *logrus.Logger
	opener      open.Opener
	loginServer *loginserver.LoginServer
	flags       *Flags
	interactive bool
}

// NewFlow creates a new login flow.
func NewFlow(opts FlowOpts) *Flow {
	if opts.Errout == nil {
		opts.Errout = os.Stderr
	}
	if opts.Prompt == nil {
		opts.Prompt = prompt.New(os.Stdin, os.Stdout)
	}
	if opts.Logger == nil {
		opts.Logger = &logrus.Logger{
			Out:   opts.Errout,
			Level: logrus.InfoLevel,
		}
	}
	if opts.Opener == nil {
		opts.Opener = open.NewOsOpener(opts.Logger)
	}
	return &Flow{
		errout: opts.Errout,
		prompt: opts.Prompt,
		logger: opts.Logger,
		opener: opts.Opener,
	}
}

// Start initiates the login flow for a given set of flags and HTTP client.
func (f *Flow) Start(flags *Flags, httpClient *httpclient.Client) (string, error) {
	if err := flags.Resolve(); err != nil {
		return "", err
	}
	f.flags = flags

	f.client = NewClient(httpClient, f.logger)
	providers, err := f.client.Providers()
	if err != nil {
		return "", err
	}

	provider, err := f.selectProvider(providers)
	if err != nil {
		return "", err
	}
	f.logger.Infof("Using login provider '%s'.", provider.Type)

	return f.triggerMethod(provider)
}

// SelectProvider explicitly, implicitly, or manually selects the provider to use for login.
func (f *Flow) selectProvider(providers Providers) (*Provider, error) {
	// Explicit provider selection.
	if f.flags.providerID != "" {
		// TODO: If a provider ID, a username, and a password are given
		// we should return an error. This might break some use cases.
		provider, ok := providers[f.flags.providerID]
		if ok {
			return provider, nil
		}
		return nil, fmt.Errorf("unknown login provider ID '%s'", f.flags.providerID)
	}

	// Extract login provider candidates for implicit or manual selection.
	var providerCandidates []*Provider
	for _, provider := range providers.Slice() {
		// If both username and password are passed, we default to dcos-uid-password.
		// The provider does not matter in the actual request we do to the cluster,
		// the IAM might delegate the credential validation to a directory backend via LDAP.
		if provider.Type == DCOSUIDPassword && f.flags.username != "" && f.flags.password != "" {
			return provider, nil
		}

		if f.flags.Supports(provider) {
			providerCandidates = append(providerCandidates, provider)
		} else {
			f.logger.Infof("Excluding provider '%s' based on command-line flags.", provider.ID)
		}
	}

	switch len(providerCandidates) {
	case 0:
		return nil, errors.New("couldn't determine a login provider")
	case 1:
		// Implicit provider selection.
		return providerCandidates[0], nil
	default:
		// Manual provider selection.
		i, err := f.prompt.Select("Please select a login method:", providerCandidates)
		if err != nil {
			return nil, err
		}
		return providerCandidates[i], nil
	}
}

// TriggerMethod initiates the client login method of a given provider.
func (f *Flow) triggerMethod(provider *Provider) (acsToken string, err error) {
	for attempt := 1; ; attempt++ {
		switch provider.ClientMethod {

		case methodCredential, methodUserCredential:
			acsToken, err = f.loginUIDPassword(provider.Config.StartFlowURL)

		case methodServiceCredential:
			acsToken, err = f.loginService()

		case methodBrowserAuthToken, methodBrowserOIDCToken:
			if attempt == 1 {
				f.initBrowserFlow(provider)
			}
			acsToken, err = f.loginBrowser(provider)
		}

		// In case of failure, let the user re-enter credentials 2 times.
		if err != nil && attempt < 3 {
			f.logger.Errorf("Error: %s", err)
		}
		if err == nil || !f.interactive || attempt >= 3 {
			return acsToken, err
		}
	}
}

// loginUIDPassword initiates a UID/password login flow.
//
// It reads UID and password from command-line flags or prompts for them.
func (f *Flow) loginUIDPassword(startFlowURL string) (string, error) {
	return f.client.Login(startFlowURL, &Credentials{
		UID:      f.uid(),
		Password: f.password(),
	})
}

// loginService initiates a login flow for service accounts.
//
// It reads UID from the command-line flags and generates a service login
// token from the --private-key. The token has a 5 minutes lifetime.
func (f *Flow) loginService() (string, error) {
	uid := f.uid()
	token, err := f.serviceToken(uid)
	if err != nil {
		return "", err
	}
	return f.client.Login("", &Credentials{UID: uid, Token: token})
}

// loginBrowser initiates a login flow for browser-based providers.
//
// It opens the browser at the `start_flow_url` location specified in the provider config.
// The user is then expected to continue the flow in the browser and copy paste the
// token from the browser to their terminal. For the auth0 provider, the login token
// will be intercepted automatically through a temporary login server running on localhost.
func (f *Flow) loginBrowser(provider *Provider) (string, error) {
	var token string

	if f.loginServer != nil {
		token = <-f.loginServer.Token()
		f.loginServer.Close()
	} else {
		token = f.prompt.Input("Enter token from the browser: ")

		// Only set interactive to true when the token comes from STDIN. In case of an error when
		// using the login server, retrying isn't needed (it can't be a typo, no copy-pasting was involved).
		f.interactive = true
	}

	// methodBrowserOIDCToken relies on a login token,
	// it must be sent in order to get an ACS token back.
	if provider.ClientMethod == methodBrowserOIDCToken {
		return f.client.Login("", &Credentials{Token: token})
	}

	// With methodBrowserAuthToken, the user is passing the authentication token from the browser
	// to the terminal directly. Send a HEAD request with an appropriate Authorization header to a
	// well-known path in order to verify the authentication token.
	var resp *http.Response
	resp, err := f.client.sniffAuth(token)
	if err != nil {
		return "", err
	}
	switch resp.StatusCode {
	case 200, 403:
		return token, nil
	case 401:
		return "", errors.New("invalid auth token")
	default:
		return "", fmt.Errorf("unexpected status code %d", resp.StatusCode)
	}
}

// initBrowserFlow initiates a browser based flow.
//
// It opens the browser and starts a local login server when applicable.
func (f *Flow) initBrowserFlow(provider *Provider) {
	startFlowURL := provider.Config.StartFlowURL

	// For the "dcos-oidc-auth0" login provider ID, we start a local web server
	// in order to avoid copy-pasting the token from the browser to the terminal.
	if provider.ID == DCOSOIDCAuth0 {
		var err error
		f.loginServer, err = loginserver.New(startFlowURL)
		if err != nil {
			f.logger.Error(err)
		} else {
			startFlowURL = f.loginServer.StartFlowURL()
			go f.loginServer.Start()
		}
	}

	err := f.openBrowser(startFlowURL)
	if err != nil {
		// Being unable to open the browser is not critical, a message was prompted
		// to the user with the URL they should go to in order to start the login flow.
		f.logger.Info(err)

		// However we close and don't use the web server in this scenario, as the CLI might
		// be running on a non-desktop environment so the server would be stuck waiting.
		// Falling back to reading from STDIN is safer here.
		//
		// See https://jira.mesosphere.com/browse/DCOS_OSS-5591
		if f.loginServer != nil {
			f.loginServer.Close()
			f.loginServer = nil
		}
	}
}

// uid returns the UID from the flag or prompts the user for it.
func (f *Flow) uid() string {
	if f.flags.username != "" {
		return f.flags.username
	}
	f.interactive = true
	return f.prompt.Input("Username: ")
}

// password returns the password from the resolved flag or prompts the user for it.
func (f *Flow) password() string {
	if f.flags.password != "" {
		return f.flags.password
	}
	f.interactive = true
	return f.prompt.Password("Password: ")
}

// serviceToken generates a login token based on a UID / service account private key.
func (f *Flow) serviceToken(uid string) (string, error) {
	return jwt.NewWithClaims(jwt.GetSigningMethod("RS256"), jwt.MapClaims{
		"uid": uid,
		"exp": time.Now().Add(5 * time.Minute).Unix(),
	}).SignedString(f.flags.privateKey)
}

// openBrowser opens the browser at a given start flow URL.
func (f *Flow) openBrowser(startFlowURL string) error {
	// The start flow URL might be a relative or absolute URL.
	if strings.HasPrefix(startFlowURL, "/") {
		req, err := f.client.http.NewRequest("GET", startFlowURL, nil)
		if err != nil {
			return err
		}
		startFlowURL = req.URL.String()
	}

	msg := "If your browser didn't open, please follow this link:\n\n    %s\n\n"
	fmt.Fprintf(f.errout, msg, startFlowURL)

	if err := f.opener.Open(startFlowURL); err != nil {
		return err
	}
	return nil
}
