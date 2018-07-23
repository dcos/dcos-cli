package plugin

import (
	"fmt"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"

	"github.com/pelletier/go-toml"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
)

// Manager retrieves the plugins available for the current cluster
// by navigating into the filesystem.
type Manager struct {
	Fs     afero.Fs
	Logger *logrus.Logger
	Dir    string
}

// Remove removes a plugin from the filesystem.
func (m *Manager) Remove(name string) error {
	pluginDir := filepath.Join(m.Dir, name)
	pluginDirExists, err := afero.DirExists(m.Fs, pluginDir)
	if err != nil {
		return err
	}
	if !pluginDirExists {
		return fmt.Errorf("'%s' is not a plugin directory", pluginDir)
	}
	return m.Fs.RemoveAll(pluginDir)
}

// Plugins returns the plugins associated with the current cluster.
func (m *Manager) Plugins() (plugins []*Plugin) {
	pluginDirs, err := afero.ReadDir(m.Fs, m.Dir)
	if err != nil {
		m.Logger.Debugf("Couldn't open plugin dir: %s", err)
		return plugins
	}

	for _, pluginDir := range pluginDirs {
		if !pluginDir.IsDir() {
			continue
		}
		plugin, err := m.loadPlugin(pluginDir.Name())
		if err != nil {
			// We don't want to see the CLI failing if a single plugin is malformed.
			// We thus log the error but continue if there is an issue at that step.
			m.Logger.Debugf("Couldn't load plugin: %s", err)
			continue
		}
		plugins = append(plugins, plugin)
	}
	return plugins
}

// loadPlugin loads a plugin based on its name.
func (m *Manager) loadPlugin(name string) (*Plugin, error) {
	m.Logger.Infof("Loading plugin '%s'...", name)

	plugin := &Plugin{Name: name}
	pluginPath := filepath.Join(m.Dir, name, "env")
	pluginFilePath := filepath.Join(pluginPath, "plugin.toml")

	if err := m.unmarshalPlugin(plugin, pluginFilePath); err != nil {
		return nil, err
	}
	persistedPlugin := *plugin

	if len(plugin.Commands) == 0 {
		plugin.Commands = m.findCommands(pluginPath)
	}

	for _, cmd := range plugin.Commands {
		if !filepath.IsAbs(cmd.Path) {
			cmd.Path = filepath.Join(pluginPath, cmd.Path)
		}
		if cmd.Description == "" {
			cmd.Description = m.commandDescription(cmd)
		}
	}

	if !reflect.DeepEqual(persistedPlugin, *plugin) {
		m.unmarshalPlugin(plugin, pluginFilePath)
	}
	return plugin, nil
}

// findCommands discovers commands in a given directory according to conventions.
// Each command should be contained in a dedicated binary named `dcos-{command}`.
// On Windows it must have the `.exe`` extension.
func (m *Manager) findCommands(pluginDir string) (commands []*Command) {
	binDir := filepath.Join(pluginDir, "bin")
	if runtime.GOOS == "windows" {
		binDir = filepath.Join(pluginDir, "Scripts")
	}

	m.Logger.Debugf("Discovering commands in '%s'...", binDir)

	binaries, err := afero.ReadDir(m.Fs, binDir)
	if err != nil {
		return nil
	}

	for _, binary := range binaries {
		if !strings.HasPrefix(binary.Name(), "dcos-") {
			continue
		}
		cmd := &Command{
			Path: filepath.Join(binDir, binary.Name()),
			Name: strings.TrimPrefix(binary.Name(), "dcos-"),
		}
		if runtime.GOOS == "windows" {
			cmd.Name = strings.TrimSuffix(cmd.Name, ".exe")
		}
		m.Logger.Debugf("Discovered '%s' command", cmd.Name)
		commands = append(commands, cmd)
	}
	return commands
}

// commandDescription gets the command info summary by invoking the binary with the `--info` flag.
func (m *Manager) commandDescription(cmd *Command) (desc string) {
	infoCmd, err := exec.Command(cmd.Path, cmd.Name, "--info").Output()
	if err != nil {
		m.Logger.Debugf("Couldn't get info summary for the '%s' command: %s", cmd.Name, err)
	} else {
		desc = strings.TrimSpace(string(infoCmd))
	}
	return desc
}

// unmarshalPlugin unmarshals a `plugin.toml` file into a Plugin structure.
func (m *Manager) unmarshalPlugin(plugin *Plugin, path string) error {
	data, err := afero.ReadFile(m.Fs, path)
	if err != nil {
		m.Logger.Debugf("Couldn't open plugin.toml: %s", err)
		return nil
	}
	return toml.Unmarshal(data, plugin)
}

// persistPlugin saves a `plugin.toml` file representing the plugin.
func (m *Manager) persistPlugin(plugin *Plugin, path string) {
	pluginTOML, err := toml.Marshal(*plugin)
	if err == nil {
		err = afero.WriteFile(m.Fs, path, pluginTOML, 0644)
	}
	if err != nil {
		m.Logger.Debug(err)
	}
}
