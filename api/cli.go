package api

import (
	"io"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/dcos/dcos-cli/pkg/open"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/dcos/dcos-cli/pkg/prompt"
	"github.com/dcos/dcos-cli/pkg/setup"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
)

// Context contains abstractions for stdout/stderr, the filesystem, and the CLI environment in general.
// It also acts as a factory/helper for various objects across the project. It has quite wide scope so
// in the future it might be refined or interfaces might be introduced for subsets of its functionalities.
type Context interface {
	// Args returns the command-line arguments, starting with the program name.
	Args() []string

	// Input returns the reader for CLI input.
	Input() io.Reader

	// Out returns a writer for CLI output.
	Out() io.Writer

	// ErrOut returns a writer for CLI errors, logs, and informational messages.
	ErrOut() io.Writer

	// EnvLookup lookups environment variables.
	EnvLookup(key string) (string, bool)

	// Fs returns the filesystem.
	Fs() afero.Fs

	// Logger returns the CLI logger.
	Logger() *logrus.Logger

	// DCOSDir returns the root directory for the DC/OS CLI.
	DCOSDir() string

	// ConfigManager returns the ConfigManager for the context.
	ConfigManager() *config.Manager

	// Cluster returns the current cluster.
	Cluster() (*config.Cluster, error)

	// Clusters returns the configured clusters.
	Clusters() []*config.Cluster

	// HTTPClient creates an httpclient.Client for a given cluster.
	HTTPClient(c *config.Cluster, opts ...httpclient.Option) *httpclient.Client

	// Prompt returns a *prompt.Prompt.
	Prompt() *prompt.Prompt

	// Opener returns an open.Opener.
	Opener() open.Opener

	// PluginManager returns a plugin manager.
	PluginManager(*config.Cluster) *plugin.Manager

	// Login initiates a login based on a set of flags and HTTP client. On success it returns an ACS token.
	Login(flags *login.Flags, httpClient *httpclient.Client) (string, error)

	// Setup configures a given cluster based on its URL and setup flags.
	Setup(flags *setup.Flags, clusterURL string, attach bool) (*config.Cluster, error)
}
