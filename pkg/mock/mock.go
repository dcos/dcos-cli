package mock

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"net/http"
	"net/http/httptest"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cluster/linker"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/sirupsen/logrus"
	logrustest "github.com/sirupsen/logrus/hooks/test"
	"github.com/spf13/afero"
)

// Cluster is the mock definition for a DC/OS cluster.
type Cluster struct {
	Version        string
	LoginProviders login.Providers
	AuthChallenge  string
	Links          []*linker.Link
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

	if cluster.Links != nil {
		mux.HandleFunc("/cluster/v1/links", func(w http.ResponseWriter, req *http.Request) {
			json.NewEncoder(w).Encode(&linker.Links{Links: cluster.Links})
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
	}
}

// Context is an api.Context which can be mocked.
type Context struct {
	*cli.Context
	logger     *logrus.Logger
	loggerHook *logrustest.Hook
	cluster    *config.Cluster
	clusters   []*config.Cluster
}

// NewContext returns a new mock context.
func NewContext(environment *cli.Environment) *Context {
	if environment == nil {
		environment = NewEnvironment()
	}
	logger, hook := logrustest.NewNullLogger()
	return &Context{
		Context:    cli.NewContext(environment),
		logger:     logger,
		loggerHook: hook,
	}
}

// SetCluster sets the current CLI cluster.
func (ctx *Context) SetCluster(cluster *config.Cluster) {
	ctx.cluster = cluster
}

// Cluster returns the current cluster.
func (ctx *Context) Cluster() (*config.Cluster, error) {
	if ctx.cluster != nil {
		return ctx.cluster, nil
	}
	return ctx.Context.Cluster()
}

// SetClusters sets the CLI clusters.
func (ctx *Context) SetClusters(clusters []*config.Cluster) {
	ctx.clusters = clusters
}

// Clusters returns the configured clusters.
func (ctx *Context) Clusters() ([]*config.Cluster, error) {
	if ctx.clusters != nil {
		return ctx.clusters, nil
	}
	return ctx.Context.Clusters()
}

// Logger returns the logger.
func (ctx *Context) Logger() *logrus.Logger {
	return ctx.logger
}

// LoggerHook returns the logger hook.
func (ctx *Context) LoggerHook() *logrustest.Hook {
	return ctx.loggerHook
}
