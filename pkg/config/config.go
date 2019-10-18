package config

import (
	"bytes"
	"errors"
	"io"
	"os"
	"sort"
	"strings"

	"github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"github.com/spf13/cast"
)

// TOML keys for the DC/OS configuration.
const (
	keyURL            = "core.dcos_url"
	keyACSToken       = "core.dcos_acs_token" // nolint: gosec
	keyTLS            = "core.ssl_verify"
	keyTimeout        = "core.timeout"
	keySSHUser        = "core.ssh_user"
	keySSHProxyHost   = "core.ssh_proxy_ip"
	keyPagination     = "core.pagination"
	keyReporting      = "core.reporting"
	keyMesosMasterURL = "core.mesos_master_url"
	keyPromptLogin    = "core.prompt_login"
	keyClusterName    = "cluster.name"
)

// Environment variables for the DC/OS configuration.
const (
	envTLS     = "DCOS_SSL_VERIFY"
	envTimeout = "DCOS_TIMEOUT"
)

// Errors related to the Config.
var (
	ErrNoConfigPath = errors.New("no path specified for the config")
)

// Opts are functional options for a Config.
type Opts struct {
	// EnvWhitelist is a map of config keys and environment variables.
	// When present, these env vars take precedence over the values in the toml.Tree.
	EnvWhitelist map[string]string

	// EnvLookup is the function used to lookup environment variables.
	// When not set it defaults to os.LookupEnv.
	EnvLookup func(key string) (string, bool)

	// Fs is an abstraction for the filesystem. All filesystem operations
	// for the store should be done through it instead of the os package.
	Fs afero.Fs
}

// Config is the backend for Config data. It aggregates multiple sources (env vars, TOML document)
// and is able to get/set/unset key(s) in the TOML document.
type Config struct {
	path         string
	tree         *toml.Tree
	envWhitelist map[string]string
	envLookup    func(key string) (string, bool)
	fs           afero.Fs
}

// New creates a Config based on functional options.
func New(opts Opts) *Config {
	if opts.EnvWhitelist == nil {
		opts.EnvWhitelist = map[string]string{
			keyTLS:     envTLS,
			keyTimeout: envTimeout,
		}
	}

	if opts.EnvLookup == nil {
		opts.EnvLookup = os.LookupEnv
	}

	if opts.Fs == nil {
		opts.Fs = afero.NewOsFs()
	}

	tree, _ := toml.TreeFromMap(make(map[string]interface{}))

	return &Config{
		tree:         tree,
		envWhitelist: opts.EnvWhitelist,
		envLookup:    opts.EnvLookup,
		fs:           opts.Fs,
	}
}

// Empty returns an empty config store.
func Empty() *Config {
	return New(Opts{})
}

// Keys returns the possible config keys.
func Keys() map[string]string {
	return map[string]string{
		keyACSToken:       "the DC/OS authentication token",
		keyURL:            "the public master URL of your DC/OS cluster",
		keyMesosMasterURL: "the Mesos master URL (defaults to 'core.dcos_url')",
		keyPagination:     "indicates whether to paginate output (defaults to true)",
		keyTLS:            "indicates whether to verify SSL certificates or set the path to the SSL certificates",
		keyTimeout:        "the request timeout in seconds, with a minimum value of 1 second (defaults to 3 minutes)",
		keySSHUser:        "the user used when using ssh to connect to a node of your DC/OS cluster (defaults to 'core')",
		keySSHProxyHost:   "whether to use a fixed ssh proxy host (Bastion) for node SSH access",
		keyReporting:      "whether to report usage events to Mesosphere",
		keyPromptLogin:    "whether to prompt the user to log in when token expired, otherwise automatically initiate login",
		keyClusterName:    "human readable name of cluster",

		// These are configuration sections for the dcos-core-cli plugin.
		// Ideally they should be defined by the plugin itself in its plugin.toml file.
		"job.url":            "API URL for talking to the Metronome scheduler",
		"job.service_name":   "the name of the metronome cluster",
		"marathon.url":       "base URL for talking to Marathon, overwrites the value specified in 'core.dcos_url'",
		"package.cosmos_url": "base URL for talking to Cosmos, overwrites the value specified in 'core.dcos_url'",
	}
}

// LoadPath populates the store based on a path to a TOML file.
// If the file doesn't exist, an empty one is created.
func (c *Config) LoadPath(path string) error {
	f, err := c.fs.OpenFile(path, os.O_RDONLY|os.O_CREATE, 0600)
	if err != nil {
		return err
	}
	defer f.Close()

	if err := c.LoadReader(f); err != nil {
		return err
	}
	c.path = path
	return nil
}

// LoadReader populates the store based on an io.Reader containing TOML data.
func (c *Config) LoadReader(reader io.Reader) error {
	tree, err := toml.LoadReader(reader)
	if err != nil {
		return err
	}
	c.LoadTree(tree)
	return nil
}

// LoadTree populates the store with a TOML tree.
func (c *Config) LoadTree(tree *toml.Tree) {
	c.tree = tree
}

// Path returns the path to the Config.
func (c *Config) Path() string {
	return c.path
}

// SetPath assigns a path to the Config.
func (c *Config) SetPath(path string) {
	c.path = path
}

// Fs returns the filesystem for the store.
func (c *Config) Fs() afero.Fs {
	return c.fs
}

// Get returns a value from the Config using a key.
func (c *Config) Get(key string) interface{} {
	// Check if the given key is whitelisted as an env var.
	if envVar, ok := c.envWhitelist[key]; ok {
		// If so, look-it up.
		if envVal, ok := c.envLookup(envVar); ok {
			return envVal
		}
	}

	// Fallback to the TOML tree if present.
	switch node := c.tree.Get(key).(type) {
	case *toml.Tree, []*toml.Tree:
		return nil
	default:
		return node
	}
}

// ToMap recursively generates a representation of the config using Go built-in structures.
func (c *Config) ToMap() map[string]interface{} {
	return c.tree.ToMap()
}

// Set sets a key in the store.
func (c *Config) Set(key string, val interface{}) (err error) {
	switch key {
	case keyURL:
		// Make sure the ACS token is unset whenever the DC/OS URL is updated.
		c.Unset(keyACSToken)
	case keyTimeout:
		// go-toml requires int64
		val, err = cast.ToInt64E(val)
	case keyTLS:
		if _, err = cast.ToBoolE(val); err != nil {
			_, err = c.fs.Stat(cast.ToString(val))
		}
	case keyPagination, keyReporting, keyPromptLogin:
		val, err = cast.ToBoolE(val)
	default:
		val, err = cast.ToStringE(val)
	}
	if err == nil {
		c.tree.Set(key, val)
	}
	return err
}

// Unset deletes a given key from the Config.
func (c *Config) Unset(key string) {
	if key == keyURL {
		// Unset the ACS token as well when removing the DC/OS URL.
		c.Unset(keyACSToken)
	}
	keys := strings.Split(key, ".")

	treeMap := c.tree.ToMap()
	subMap := treeMap

	// Extract a sub-map for each dotted key section.
	for i, key := range keys {
		if node, ok := subMap[key]; ok {
			switch nodeType := node.(type) {
			case map[string]interface{}:
				subMap = nodeType
			default:
				// Abort if the section is not a map, unless it's the last section.
				if i == len(keys)-1 {
					// Remove the key from the parent map and swap trees.
					delete(subMap, key)
					c.tree, _ = toml.TreeFromMap(treeMap)
				} else {
					return
				}
			}
		}
	}
}

// Persist flushes the in-memory TOML tree representation to the path associated to the Config.
func (c *Config) Persist() error {
	if c.path == "" {
		return ErrNoConfigPath
	}
	var buf bytes.Buffer
	if _, err := c.tree.WriteTo(&buf); err != nil {
		return err
	}
	return afero.WriteFile(c.fs, c.path, buf.Bytes(), 0600)
}

// Keys returns all the keys in the Config.
func (c *Config) Keys() []string {
	var keys []string
	for key, envVar := range c.envWhitelist {
		if _, ok := c.envLookup(envVar); ok {
			keys = append(keys, key)
		}
	}

	searchKeys(c.tree, &keys, []string{})
	keysLen := len(keys)
	if keysLen < 2 {
		// Less than 2 keys, no need to sort or remove duplicates.
		return keys
	}

	sort.Strings(keys)

	// Remove duplicates, this happens when there is both an env var and a TOML key.
	// Keys are already sorted so this is done by comparing each key with the next one
	// and removing the latter if it's the same.
	for i := 1; i < keysLen; i++ {
		if keys[i] == keys[i-1] {
			keys = append(keys[:i], keys[i+1:]...)
			keysLen--
		}
	}
	return keys
}

// searchKeys walks recursively through a toml.Tree and appends the full path to each leaf into keys.
func searchKeys(tree *toml.Tree, keys *[]string, keyPath []string) {
	for _, key := range tree.Keys() {
		childKeyPath := append(keyPath, key)
		switch node := tree.Get(key).(type) {
		case *toml.Tree:
			searchKeys(node, keys, childKeyPath)
		default:
			*keys = append(*keys, strings.Join(childKeyPath, "."))
		}
	}
}
