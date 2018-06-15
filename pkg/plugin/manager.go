package plugin

import (
	"fmt"
	"io/ioutil"
	"path/filepath"

	"github.com/spf13/afero"
	"github.com/spf13/cobra"
	yaml "gopkg.in/yaml.v2"
)

// ManagerOpts defines the options available to the plugin Manager.
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

// Manager is able to find, install, and delete plugins
type Manager struct {
	fs  afero.Fs
	dir string
}

// NewManager creates a plugin manager
func NewManager(opts ManagerOpts) *Manager {
	if opts.Fs == nil {
		opts.Fs = afero.NewOsFs()
	}

	return &Manager{
		fs:  opts.Fs,
		dir: opts.Dir,
	}
}

// Plugins returns all plugins for the current cluster
func (m *Manager) Plugins() []*Plugin {
	plugins := []*Plugin{}

	pluginDir, err := m.fs.Open(m.dir)
	if err != nil {
		return []*Plugin{}
	}
	defer pluginDir.Close()

	pluginsDirInfo, err := pluginDir.Readdir(-1)
	if err != nil {
		return plugins
	}

	for _, pluginDirInfo := range pluginsDirInfo {
		if pluginDirInfo.IsDir() {
			definitionFilePath := filepath.Join(m.dir, pluginDirInfo.Name(), "plugin.yaml")
			data, err := ioutil.ReadFile(definitionFilePath)
			if err != nil {
				fmt.Println(err)
				continue
			}

			var plugin *Plugin
			if err = yaml.Unmarshal(data, &plugin); err != nil {
				fmt.Println(err)
				continue
			}

			// set plugin directory
			plugin.dir = filepath.Join(m.dir, pluginDirInfo.Name())

			plugins = append(plugins, plugin)
		}
	}

	return plugins
}

// CreateCommands creates a list cobra command corresponding to the commands available in the plugin.
func (m *Manager) CreateCommands() []*cobra.Command {
	plugins := m.Plugins()

	commands := []*cobra.Command{}

	for _, p := range plugins {
		commands = append(commands, p.IntoCommands()...)
	}

	return commands
}
