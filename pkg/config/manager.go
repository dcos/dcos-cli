package config

import (
	"errors"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/afero"
)

// ManagerOpts are functional options for a Manager.
type ManagerOpts struct {
	// Fs is an abstraction for the filesystem. All filesystem operations
	// for the manager should be done through it instead of the os package.
	Fs afero.Fs

	// EnvLookup is the function used to lookup environment variables.
	// When not set it defaults to os.LookupEnv.
	EnvLookup func(key string) (string, bool)

	// Dir is the root directory for the config manager.
	Dir string
}

// Manager is able to retrieve, create, and delete configs.
type Manager struct {
	fs        afero.Fs
	envLookup func(key string) (string, bool)
	dir       string
}

// ErrConfigNotFound means that the manager cannot find a config using a name/id.
var ErrConfigNotFound = errors.New("no match found")

// ErrTooManyConfigs means that more than one config has been found for a given search.
var ErrTooManyConfigs = errors.New("multiple matches found")

// NewManager creates a new config manager.
func NewManager(opts ManagerOpts) *Manager {
	if opts.Fs == nil {
		opts.Fs = afero.NewOsFs()
	}

	if opts.EnvLookup == nil {
		opts.EnvLookup = os.LookupEnv
	}

	return &Manager{
		fs:        opts.Fs,
		dir:       opts.Dir,
		envLookup: opts.EnvLookup,
	}
}

// Current retrieves the current config.
//
// The lookup order is :
// - DCOS_CLUSTER is defined and is the name/ID of a configured cluster.
// - An attached file exists alongside a configured cluster, OR there is a single configured cluster.
func (m *Manager) Current() (*Config, error) {
	if configName, ok := m.envLookup("DCOS_CLUSTER"); ok {
		return m.Find(configName, true)
	}

	configs := m.All()
	if len(configs) == 1 {
		return configs[0], nil
	}

	var currentConfig *Config
	for _, config := range configs {
		attachedFile := m.attachedFilePath(config)
		if m.fileExists(attachedFile) {
			if currentConfig != nil {
				return nil, errors.New("multiple clusters are attached")
			}
			currentConfig = config
		}
	}
	if currentConfig == nil {
		return nil, errors.New("no cluster is attached")
	}
	return currentConfig, nil
}

// Find finds a config by cluster name or ID, `strict` indicates
// whether or not the search string can also be a cluster ID prefix.
func (m *Manager) Find(name string, strict bool) (*Config, error) {
	var matches []*Config
	for _, config := range m.All() {
		configName, _ := config.Get(keyClusterName).(string)
		if name == configName {
			matches = append(matches, config)
		}
		clusterID := filepath.Base(filepath.Dir(config.Path()))
		if clusterID == name {
			return config, nil
		}
		if !strict && strings.HasPrefix(clusterID, name) {
			matches = append(matches, config)
		}
	}

	switch len(matches) {
	case 0:
		return nil, ErrConfigNotFound
	case 1:
		return matches[0], nil
	default:
		return nil, ErrTooManyConfigs
	}
}

// All retrieves all configs.
func (m *Manager) All() (configs []*Config) {
	configsDir, err := m.fs.Open(filepath.Join(m.dir, "clusters"))
	if err != nil {
		return
	}
	defer configsDir.Close()

	configsDirInfo, err := configsDir.Readdir(-1)
	if err != nil {
		return
	}

	for _, configDirInfo := range configsDirInfo {
		if configDirInfo.IsDir() {
			config := m.newConfig()
			configPath := filepath.Join(configsDir.Name(), configDirInfo.Name(), "dcos.toml")
			if err := config.LoadPath(configPath); err == nil {
				configs = append(configs, config)
			}
		}
	}

	return
}

// Save saves a config to the disk under the given cluster ID folder.
func (m *Manager) Save(config *Config, id string, caBundle []byte) error {
	configDir := filepath.Join(m.dir, "clusters", id)
	if err := m.fs.MkdirAll(configDir, 0755); err != nil {
		return err
	}
	if len(caBundle) > 0 {
		caBundlePath := filepath.Join(configDir, "dcos_ca.crt")
		err := afero.WriteFile(m.fs, caBundlePath, caBundle, 0644)
		if err != nil {
			return err
		}
		config.Set(keyTLS, caBundlePath)
	}
	config.SetPath(filepath.Join(configDir, "dcos.toml"))
	return config.Persist()
}

// Attach sets a given config as the current one. This is done by adding an `attached`
// file next to it. If another config is already attached, the file gets moved.
func (m *Manager) Attach(config *Config) error {
	var currentAttachedFile string

	// Iterate over all configs to find the one with an attached file, if any.
	for _, c := range m.All() {
		attachedFile := m.attachedFilePath(c)
		if m.fileExists(attachedFile) {
			currentAttachedFile = attachedFile
			break
		}
	}

	configAttachedPath := m.attachedFilePath(config)

	// Create the attached file if no config is currently attached, otherwise move it.
	if currentAttachedFile == "" {
		f, err := m.fs.Create(configAttachedPath)
		if err != nil {
			return err
		}
		return f.Close()
	}
	return m.fs.Rename(currentAttachedFile, configAttachedPath)
}

// attachedFilePath returns the `attached` file path for a given config.
func (m *Manager) attachedFilePath(conf *Config) string {
	return filepath.Join(filepath.Dir(conf.Path()), "attached")
}

// fileExists returns whether or not a file exists.
func (m *Manager) fileExists(path string) bool {
	fileInfo, err := m.fs.Stat(path)
	if err != nil {
		return false
	}
	return fileInfo.Mode().IsRegular()
}

func (m *Manager) newConfig() *Config {
	return New(Opts{
		EnvLookup: m.envLookup,
		Fs:        m.fs,
	})
}
