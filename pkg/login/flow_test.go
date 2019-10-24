package login

import (
	"bytes"
	"encoding/json"
	"errors"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"

	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/login/loginserver"
	"github.com/dcos/dcos-cli/pkg/open"
	"github.com/dcos/dcos-cli/pkg/prompt"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestSelectUIDPasswordProvider(t *testing.T) {
	flow := NewFlow(FlowOpts{})
	flow.flags = NewFlags(afero.NewMemMapFs(), nil, nil)
	flow.flags.username = "hello"
	flow.flags.password = "itsme"

	providers := Providers{}

	providers["login-provider-1"] = &Provider{
		ID:           "login-provider-1",
		Type:         DCOSUIDPassword,
		Description:  "Default DC/OS login provider",
		ClientMethod: methodUserCredential,
		Config: ProviderConfig{
			StartFlowURL: "/acs/api/v1/auth/login",
		},
	}

	providers["login-provider-2"] = &Provider{
		ID:           "login-provider-2",
		Type:         DCOSUIDPassword,
		Description:  "Default DC/OS login provider",
		ClientMethod: methodUserCredential,
		Config: ProviderConfig{
			StartFlowURL: "/acs/api/v1/auth/login",
		},
	}

	provider, err := flow.selectProvider(providers)
	require.NoError(t, err)
	require.True(t, provider == providers["login-provider-1"] || provider == providers["login-provider-2"])
}

func TestTriggerMethodOIDCWithLoginServer(t *testing.T) {
	expectedLoginToken := "dummy_login_token"
	expectedACSToken := "dummy_acs_token"

	opener := open.OpenerFunc(func(resource string) error {

		startFlowURL, err := url.Parse(resource)
		require.NoError(t, err)

		loginData := &loginserver.LoginData{
			Token:     expectedLoginToken,
			CSRFToken: startFlowURL.Query().Get("dcos_cli_csrf_token"),
		}

		var buf bytes.Buffer
		err = json.NewEncoder(&buf).Encode(loginData)
		require.NoError(t, err)

		resp, err := httpclient.New("").Post(startFlowURL.Query().Get("redirect_uri"), "application/json", &buf)
		require.NoError(t, err)
		require.Equal(t, 200, resp.StatusCode)

		return nil
	})

	ts := httptest.NewServer(mockLoginEndpoint(t, expectedLoginToken, expectedACSToken))
	defer ts.Close()

	logger := &logrus.Logger{Out: ioutil.Discard}

	flow := NewFlow(FlowOpts{
		Logger: logger,
		Opener: opener,
	})

	flow.client = NewClient(httpclient.New(ts.URL), logger)

	acsToken, err := flow.triggerMethod(defaultOIDCImplicitFlowProvider())
	require.NoError(t, err)
	require.Equal(t, expectedACSToken, acsToken)
}

func TestTriggerMethodOIDCWithoutLoginServer(t *testing.T) {

	testCases := []struct {
		provider *Provider
	}{
		{
			// We're simulating a container environment where the browser can't be opened.
			// See https://jira.mesosphere.com/browse/DCOS_OSS-5591
			defaultOIDCImplicitFlowProvider(),
		},
		{
			// Non-regression test for a panic on browser login flows other than auth0.
			// https://jira.mesosphere.com/browse/DCOS-60349
			shibbolethLoginProvider(),
		},
	}

	for _, tc := range testCases {
		expectedLoginToken := "dummy_login_token"
		expectedACSToken := "dummy_acs_token"

		ts := httptest.NewServer(mockLoginEndpoint(t, expectedLoginToken, expectedACSToken))
		defer ts.Close()

		logger := &logrus.Logger{Out: ioutil.Discard}

		var in bytes.Buffer
		in.WriteString(expectedLoginToken)

		opener := open.OpenerFunc(func(_ string) error {
			return errors.New("couldn't open browser, I'm just a container")
		})

		flow := NewFlow(FlowOpts{
			Prompt: prompt.New(&in, ioutil.Discard),
			Logger: logger,
			Opener: opener,
		})

		flow.client = NewClient(httpclient.New(ts.URL), logger)

		acsToken, err := flow.triggerMethod(tc.provider)
		require.NoError(t, err)
		require.Equal(t, expectedACSToken, acsToken)
	}
}

func mockLoginEndpoint(t *testing.T, expectedLoginToken, acsToken string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc(defaultLoginEndpoint, func(w http.ResponseWriter, req *http.Request) {
		assert.Equal(t, "POST", req.Method)

		var credentials Credentials
		if err := json.NewDecoder(req.Body).Decode(&credentials); err != nil {
			w.WriteHeader(401)
			return
		}
		if !assert.Equal(t, expectedLoginToken, credentials.Token) {
			w.WriteHeader(401)
			return
		}
		var jwt JWT
		jwt.Token = acsToken
		err := json.NewEncoder(w).Encode(&jwt)
		assert.NoError(t, err)
	})
	return mux
}

func shibbolethLoginProvider() *Provider {
	return &Provider{
		ID:           "shib-integration-test",
		Type:         OIDCImplicitFlow,
		ClientMethod: methodBrowserOIDCToken,
		Config: ProviderConfig{
			StartFlowURL: "/login?redirect_uri=urn:ietf:wg:oauth:2.0:oob",
		},
	}
}
