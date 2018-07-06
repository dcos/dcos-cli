package mock

import (
	"bytes"
	"encoding/json"
	"errors"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"os/user"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/spf13/afero"
)

// Cluster is the mock definition for a DC/OS cluster.
type Cluster struct {
	Version        string
	LoginProviders login.Providers
	AuthChallenge  string
}

// NewTestServer creates a new HTTP test server based on a Cluster.
func NewTestServer(cluster Cluster) *httptest.Server {
	mux := http.NewServeMux()

	if cluster.Version != "" {
		mux.HandleFunc("/dcos-metadata/dcos-version.json", func(w http.ResponseWriter, req *http.Request) {
			version := map[string]string{"version": cluster.Version}
			json.NewEncoder(w).Encode(&version)
		})
	}

	if cluster.LoginProviders != nil {
		mux.HandleFunc("/acs/api/v1/auth/providers", func(w http.ResponseWriter, req *http.Request) {
			json.NewEncoder(w).Encode(&cluster.LoginProviders)
		})
	}

	if cluster.AuthChallenge != "" {
		mux.HandleFunc("/pkgpanda/active.buildinfo.full.json", func(w http.ResponseWriter, req *http.Request) {
			w.Header().Add("WWW-Authenticate", cluster.AuthChallenge)
			w.WriteHeader(401)
		})
	}
	return httptest.NewServer(mux)
}

// NewEnvironment returns an environment which acts as a "black hole".
func NewEnvironment() *cli.Environment {
	return &cli.Environment{
		Input:  bytes.NewReader(nil),
		Out:    ioutil.Discard,
		ErrOut: ioutil.Discard,
		Fs:     afero.NewMemMapFs(),
		EnvLookup: func(key string) (string, bool) {
			return "", false
		},
		UserLookup: func() (*user.User, error) {
			return nil, errors.New("no user")
		},
	}
}

// Context is an api.Context which can be mocked.
type Context struct {
	*cli.Context
	clusters []*config.Cluster
}

// NewContext returns a new mock context.
func NewContext(environment *cli.Environment) *Context {
	if environment == nil {
		environment = NewEnvironment()
	}
	return &Context{
		Context: cli.NewContext(environment),
	}
}

// SetClusters sets the CLI clusters.
func (ctx *Context) SetClusters(clusters []*config.Cluster) {
	ctx.clusters = clusters
}

// Clusters returns the configured clusters.
func (ctx *Context) Clusters() []*config.Cluster {
	if ctx.clusters != nil {
		return ctx.clusters
	}
	return ctx.Context.Clusters()
}
