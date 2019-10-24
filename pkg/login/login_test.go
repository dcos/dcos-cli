package login

import (
	"encoding/json"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestProviders(t *testing.T) {
	testCases := []struct {
		providersEndpoint map[string]*Provider
		authChallenge     string
		expectedProviders Providers
	}{
		{nil, "", nil},
		{nil, "unexisting-login-method", nil},
		{
			map[string]*Provider{"dcos-users": defaultDCOSUIDPasswordProvider()},
			"acsjwt",
			Providers{"dcos-users": defaultDCOSUIDPasswordProvider()},
		},
		{
			nil,
			"acsjwt",
			Providers{"dcos-users": defaultDCOSUIDPasswordProvider()},
		},
		{
			nil,
			"oauthjwt",
			Providers{"dcos-oidc-auth0": defaultOIDCImplicitFlowProvider()},
		},
	}

	for _, tc := range testCases {
		mux := http.NewServeMux()

		if tc.providersEndpoint != nil {
			mux.HandleFunc("/acs/api/v1/auth/providers", func(w http.ResponseWriter, req *http.Request) {
				assert.Equal(t, "GET", req.Method)
				err := json.NewEncoder(w).Encode(&tc.providersEndpoint)
				assert.NoError(t, err)
			})
		}

		if tc.authChallenge != "" {
			mux.HandleFunc("/pkgpanda/active.buildinfo.full.json", func(w http.ResponseWriter, req *http.Request) {
				assert.Equal(t, "HEAD", req.Method)
				assert.Equal(t, "", req.Header.Get("Authorization"))

				w.Header().Add("WWW-Authenticate", tc.authChallenge)
				w.WriteHeader(401)
			})
		}

		ts := httptest.NewServer(mux)
		defer ts.Close()

		client := NewClient(httpclient.New(ts.URL), &logrus.Logger{Out: ioutil.Discard})

		providers, err := client.Providers()
		if tc.expectedProviders != nil {
			require.NoError(t, err)
			require.Equal(t, tc.expectedProviders, providers)
		} else {
			require.Error(t, err)
		}
	}
}

func TestNoAuth(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/pkgpanda/active.buildinfo.full.json", func(w http.ResponseWriter, req *http.Request) {
		w.WriteHeader(200)
	})

	ts := httptest.NewServer(mux)
	defer ts.Close()

	client := NewClient(httpclient.New(ts.URL), &logrus.Logger{Out: ioutil.Discard})

	_, err := client.Providers()
	require.Error(t, err)
	require.Equal(t, err, ErrAuthDisabled)
}

func TestSniffAuth(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/pkgpanda/active.buildinfo.full.json", func(w http.ResponseWriter, req *http.Request) {
		assert.Equal(t, "HEAD", req.Method)
		assert.Equal(t, "token=abc", req.Header.Get("Authorization"))
		w.WriteHeader(403)
	})

	ts := httptest.NewServer(mux)
	defer ts.Close()

	client := NewClient(httpclient.New(ts.URL), &logrus.Logger{Out: ioutil.Discard})

	resp, err := client.sniffAuth("abc")
	require.NoError(t, err)
	require.Equal(t, 403, resp.StatusCode)
}

func TestChallengeAuth(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/pkgpanda/active.buildinfo.full.json", func(w http.ResponseWriter, req *http.Request) {
		assert.Equal(t, "HEAD", req.Method)

		_, ok := req.Header["Authorization"]
		assert.False(t, ok)
		w.WriteHeader(403)
	})

	ts := httptest.NewServer(mux)
	defer ts.Close()

	client := NewClient(httpclient.New(ts.URL, httpclient.ACSToken("abc")), &logrus.Logger{Out: ioutil.Discard})

	resp, err := client.sniffAuth("")
	require.NoError(t, err)
	require.Equal(t, 403, resp.StatusCode)
}
