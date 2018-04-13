package cli

import (
	"crypto/tls"
	"io"
	"os"
	"os/user"
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/spf13/afero"
)

// Context contains abstractions for stdout/stderr, the filesystem, and the CLI environment in general.
// It also acts as a factory/helper for various objects across the project. It has quite wide scope so
// in the future it might be refined or interfaces might be introduced for subsets of its functionalities.
type Context struct {
	Out       io.Writer
	ErrOut    io.Writer
	EnvLookup func(key string) (string, bool)
	User      *user.User
	Fs        afero.Fs
}

// DefaultContext returns the default context, backed by the os package.
func DefaultContext() *Context {
	// Not being able to get the current user is not critical. While it is very unlikely to happen,
	// the context can use alternatives in such cases. See for example DCOSDir where it can use an
	// environment variable or default to the current directory when ~/.dcos is not resolvable.
	//
	// Once we have a logging system this is an error we should log though.
	usr, _ := user.Current()

	return &Context{
		Out:       os.Stdout,
		ErrOut:    os.Stderr,
		EnvLookup: os.LookupEnv,
		User:      usr,
		Fs:        afero.NewOsFs(),
	}
}

// DCOSDir returns the root directory for the DC/OS CLI.
// It defaults to `~/.dcos` and can be overriden by the `DCOS_DIR` env var.
func (ctx *Context) DCOSDir() string {
	if dcosDir, ok := ctx.EnvLookup("DCOS_DIR"); ok {
		return dcosDir
	}
	if ctx.User != nil {
		return filepath.Join(ctx.User.HomeDir, ".dcos")
	}
	return ""
}

// ConfigManager returns the ConfigManager for the context.
func (ctx *Context) ConfigManager() *config.Manager {
	return config.NewManager(config.ManagerOpts{
		Fs:        ctx.Fs,
		EnvLookup: ctx.EnvLookup,
		Dir:       ctx.DCOSDir(),
	})
}

// Cluster returns the current cluster.
func (ctx *Context) Cluster() (*Cluster, error) {
	conf, err := ctx.ConfigManager().Current()
	if err != nil {
		return nil, err
	}
	return NewCluster(conf), nil
}

// Clusters returns the clusters.
func (ctx *Context) Clusters() []*Cluster {
	confs := ctx.ConfigManager().All()
	var clusters []*Cluster
	for _, conf := range confs {
		clusters = append(clusters, NewCluster(conf))
	}

	return clusters
}

// HTTPClient creates an httpclient.Client for a given cluster.
func (ctx *Context) HTTPClient(c *Cluster, opts ...httpclient.Option) *httpclient.Client {
	if c.Timeout() > 0 {
		timeoutOpt := httpclient.Timeout(c.Timeout())
		opts = append([]httpclient.Option{timeoutOpt}, opts...)
	}
	tlsOpt := httpclient.TLS(&tls.Config{
		InsecureSkipVerify: c.TLS().Insecure,
		RootCAs:            c.TLS().RootCAs,
	})

	opts = append([]httpclient.Option{tlsOpt}, opts...)
	return httpclient.New(c.URL(), opts...)
}
