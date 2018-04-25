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
	fixtures := []struct {
		providersEndpoint map[string]*Provider
		authChallenge     string
		expectedProviders map[string]*Provider
	}{
		{nil, "", nil},
		{nil, "unexisting-login-method", nil},
		{
			map[string]*Provider{"dcos-users": defaultDCOSUIDPasswordProvider()},
			"",
			map[string]*Provider{"dcos-users": defaultDCOSUIDPasswordProvider()},
		},
		{
			nil,
			"acsjwt",
			map[string]*Provider{"dcos-users": defaultDCOSUIDPasswordProvider()},
		},
		{
			nil,
			"oauthjwt",
			map[string]*Provider{"dcos-oidc": defaultOIDCImplicitFlowProvider()},
		},
	}

	for _, fixture := range fixtures {
		mux := http.NewServeMux()

		if fixture.providersEndpoint != nil {
			mux.HandleFunc("/acs/api/v1/auth/providers", func(w http.ResponseWriter, req *http.Request) {
				assert.Equal(t, "GET", req.Method)
				err := json.NewEncoder(w).Encode(&fixture.providersEndpoint)
				assert.NoError(t, err)
			})
		}

		if fixture.authChallenge != "" {
			mux.HandleFunc("/pkgpanda/active.buildinfo.full.json", func(w http.ResponseWriter, req *http.Request) {
				assert.Equal(t, "HEAD", req.Method)
				w.Header().Add("WWW-Authenticate", fixture.authChallenge)
				w.WriteHeader(401)
			})
		}

		ts := httptest.NewServer(mux)
		defer ts.Close()

		client := NewClient(httpclient.New(ts.URL), &logrus.Logger{Out: ioutil.Discard})

		providers, err := client.Providers()
		if fixture.expectedProviders != nil {
			require.NoError(t, err)
			require.Equal(t, fixture.expectedProviders, providers)
		} else {
			require.Error(t, err)
		}
	}
}
