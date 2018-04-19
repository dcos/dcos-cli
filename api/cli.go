package api

import (
	"io"
	"os/user"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
)

// Context contains abstractions for stdout/stderr, the filesystem, and the CLI environment in general.
// It also acts as a factory/helper for various objects across the project. It has quite wide scope so
// in the future it might be refined or interfaces might be introduced for subsets of its functionalities.
type Context interface {

	// Out returns a writer for CLI output.
	Out() io.Writer

	// ErrOut returns a writer for CLI errors, logs, and informational messages.
	ErrOut() io.Writer

	// EnvLookup lookups environment variables.
	EnvLookup(key string) (string, bool)

	// User returns the current system user.
	User() (*user.User, error)

	// Fs returns the filesystem.
	Fs() afero.Fs

	// Logger returns the CLI logger.
	Logger() *logrus.Logger

	// DCOSDir returns the root directory for the DC/OS CLI.
	DCOSDir() string

	// ConfigManager returns the ConfigManager for the context.
	ConfigManager() *config.Manager

	// Cluster returns the current cluster.
	Cluster() (*cli.Cluster, error)

	// Clusters returns the configured clusters.
	Clusters() []*cli.Cluster

	// HTTPClient creates an httpclient.Client for a given cluster.
	HTTPClient(c *cli.Cluster, opts ...httpclient.Option) *httpclient.Client
}
