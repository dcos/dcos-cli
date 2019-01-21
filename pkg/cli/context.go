package cli

import (
	"crypto/tls"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/log"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/dcos/dcos-cli/pkg/open"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/dcos/dcos-cli/pkg/prompt"
	"github.com/dcos/dcos-cli/pkg/setup"
	"github.com/mitchellh/go-homedir"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
)

// Context provides an implementation of api.Context. It relies on an Environment and is used to create
// various objects across the project and is being passed to every command as a constructor argument.
type Context struct {
	env      *Environment
	logger   *logrus.Logger
	loggerMu sync.Mutex
}

// NewContext creates a new context from a given environment.
func NewContext(env *Environment) *Context {
	return &Context{env: env}
}

// Args returns the command-line arguments, starting with the program name.
func (ctx *Context) Args() []string {
	return ctx.env.Args
}

// Input returns the reader for CLI input.
func (ctx *Context) Input() io.Reader {
	return ctx.env.Input
}

// Out returns the writer for CLI output.
func (ctx *Context) Out() io.Writer {
	return ctx.env.Out
}

// ErrOut returns the writer for CLI errors, logs, and informational messages.
func (ctx *Context) ErrOut() io.Writer {
	return ctx.env.ErrOut
}

// EnvLookup lookups environment variables.
func (ctx *Context) EnvLookup(key string) (string, bool) {
	return ctx.env.EnvLookup(key)
}

// Fs returns the filesystem.
func (ctx *Context) Fs() afero.Fs {
	return ctx.env.Fs
}

// Logger returns the CLI logger.
func (ctx *Context) Logger() *logrus.Logger {
	ctx.loggerMu.Lock()
	defer ctx.loggerMu.Unlock()

	if ctx.logger == nil {
		ctx.logger = &logrus.Logger{
			Out:       ctx.env.ErrOut,
			Formatter: &log.Formatter{},
			Hooks:     make(logrus.LevelHooks),
		}
	}
	return ctx.logger
}

// PluginManager returns a plugin manager.
func (ctx *Context) PluginManager(cluster *config.Cluster) *plugin.Manager {
	pluginManager := plugin.NewManager(ctx.Fs(), ctx.Logger())
	if cluster != nil {
		pluginManager.SetCluster(cluster)
	}
	return pluginManager
}

// DCOSDir returns the root directory for the DC/OS CLI.
// It defaults to `~/.dcos` and can be overriden by the `DCOS_DIR` env var.
func (ctx *Context) DCOSDir() (string, error) {
	if dcosDir, ok := ctx.env.EnvLookup(EnvDCOSDir); ok {
		// Make sure DCOS_DIR is an absolute path, otherwise this causes issues with plugin invocation.
		// See https://jira.mesosphere.com/browse/DCOS_OSS-4405
		if !filepath.IsAbs(dcosDir) {
			currentDir, err := os.Getwd()
			if err != nil {
				return "", err
			}
			dcosDir = filepath.Join(currentDir, dcosDir)
		}
		return dcosDir, nil
	}

	// We use github.com/mitchellh/go-homedir as os/user doesn't work well with cross-compilation.
	homeDir, err := homedir.Dir()
	if err != nil {
		return "", err
	}
	return filepath.Join(homeDir, ".dcos"), nil
}

// ConfigManager returns the ConfigManager for the context.
func (ctx *Context) ConfigManager() (*config.Manager, error) {
	dcosDir, err := ctx.DCOSDir()
	if err != nil {
		return nil, err
	}
	return config.NewManager(config.ManagerOpts{
		Fs:        ctx.env.Fs,
		EnvLookup: ctx.env.EnvLookup,
		Dir:       dcosDir,
	}), nil
}

// Cluster returns the current cluster.
func (ctx *Context) Cluster() (*config.Cluster, error) {
	configManager, err := ctx.ConfigManager()
	if err != nil {
		return nil, err
	}
	conf, err := configManager.Current()
	if err != nil {
		return nil, err
	}
	return config.NewCluster(conf), nil
}

// Clusters returns the clusters.
func (ctx *Context) Clusters() ([]*config.Cluster, error) {
	configManager, err := ctx.ConfigManager()
	if err != nil {
		return nil, err
	}
	var clusters []*config.Cluster
	for _, conf := range configManager.All() {
		clusters = append(clusters, config.NewCluster(conf))
	}
	return clusters, nil
}

// HTTPClient creates an httpclient.Client for a given cluster.
func (ctx *Context) HTTPClient(c *config.Cluster, opts ...httpclient.Option) *httpclient.Client {
	var baseOpts []httpclient.Option

	if c.ACSToken() != "" {
		baseOpts = append(baseOpts, httpclient.ACSToken(c.ACSToken()))
	}
	if c.Timeout() > 0 {
		baseOpts = append(baseOpts, httpclient.Timeout(c.Timeout()))
	}
	tlsOpt := httpclient.TLS(&tls.Config{
		InsecureSkipVerify: c.TLS().Insecure,
		RootCAs:            c.TLS().RootCAs,
	})

	baseOpts = append(baseOpts, tlsOpt, httpclient.Logger(ctx.Logger()))
	opts = append(baseOpts, opts...)

	return httpclient.New(c.URL(), opts...)
}

// Prompt is able to prompt for input, password or choices.
func (ctx *Context) Prompt() *prompt.Prompt {
	return prompt.New(ctx.Input(), ctx.Out())
}

// Opener returns a new OS Opener.
func (ctx *Context) Opener() open.Opener {
	return open.NewOsOpener(ctx.Logger())
}

// Login initiates a login based on a set of flags and HTTP client. On success it returns an ACS token.
func (ctx *Context) Login(flags *login.Flags, httpClient *httpclient.Client) (string, error) {
	return ctx.loginFlow().Start(flags, httpClient)
}

// Setup configures a given cluster based on its URL and setup flags.
func (ctx *Context) Setup(flags *setup.Flags, clusterURL string, attach bool) (*config.Cluster, error) {
	configManager, err := ctx.ConfigManager()
	if err != nil {
		return nil, err
	}

	if !strings.HasPrefix(clusterURL, "https://") && !strings.HasPrefix(clusterURL, "http://") {
		ctx.Logger().Info("Missing scheme in cluster URL, assuming HTTPS.")
		clusterURL = "https://" + clusterURL
	}

	return setup.New(setup.Opts{
		Fs:            ctx.Fs(),
		Errout:        ctx.ErrOut(),
		EnvLookup:     ctx.EnvLookup,
		Prompt:        ctx.Prompt(),
		Logger:        ctx.Logger(),
		LoginFlow:     ctx.loginFlow(),
		ConfigManager: configManager,
		PluginManager: ctx.PluginManager(nil),
	}).Configure(flags, clusterURL, attach)
}

func (ctx *Context) loginFlow() *login.Flow {
	return login.NewFlow(login.FlowOpts{
		Errout: ctx.ErrOut(),
		Prompt: ctx.Prompt(),
		Logger: ctx.Logger(),
		Opener: ctx.Opener(),
	})
}

// Deprecated warns that a feature is deprecated.
// It returns an error when DCOS_CLI_STRICT_DEPRECATIONS=1.
func (ctx *Context) Deprecated(msg string) error {
	fmt.Fprintln(ctx.ErrOut(), msg)
	if _, ok := ctx.env.EnvLookup(EnvStrictDeprecations); ok {
		return errors.New("usage of deprecated feature")
	}
	return nil
}
