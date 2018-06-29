package plugin

import (
	"encoding/json"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	yaml "gopkg.in/yaml.v2"
)

// Manager retrieves the plugins available for the current cluster
// by navigating into the filesystem. It requires a `plugin.yaml` file for
// each plugin, and can create this file if it doesn't exist yet.
type Manager struct {
	Fs     afero.Fs
	Logger *logrus.Logger
	Dir    string
	Stdout io.Writer
	Stderr io.Writer
	Stdin  io.Reader
}

// Package represents information of old plugins found in Universe packages.
type Package struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Version     string `json:"version"`
}

// Plugins returns the plugins associated with the current cluster.
func (m *Manager) Plugins() []*Plugin {
	plugins := []*Plugin{}

	pluginsDirHandle, err := m.Fs.Open(m.Dir)
	if err != nil {
		// If we fail to open the directory, we return an empty list.
		return plugins
	}
	defer pluginsDirHandle.Close()

	pluginDirs, err := pluginsDirHandle.Readdir(0)
	if err != nil {
		// If we fail to open the directory, we return an empty list.
		return plugins
	}

	for _, pluginDir := range pluginDirs {
		if pluginDir.IsDir() {
			plugin := &Plugin{}

			// Set plugin directories.
			plugin.dir = filepath.Join(m.Dir, pluginDir.Name())
			plugin.BinDir = filepath.Join(plugin.dir, "env", "bin")

			if runtime.GOOS == "windows" {
				exists, _ := afero.DirExists(m.Fs, plugin.BinDir)
				if !exists {
					plugin.BinDir = filepath.Join(plugin.dir, "env", "Scripts")
				}
			}

			pluginFilePath := filepath.Join(plugin.dir, "env", "plugin.yaml")
			data, err := afero.ReadFile(m.Fs, pluginFilePath)
			if err == nil {
				// We don't want to see the CLI failing if a single plugin is malformed.
				// We thus log the error but continue if there is an issue at that step.
				err = yaml.Unmarshal(data, plugin)
				if err != nil {
					m.Logger.Warning(err)
					continue
				}
			} else {
				// plugin.yaml not found, try loading it as an old Universe package.
				err = m.loadPluginFromPackage(plugin)
				if err != nil {
					m.Logger.Warning(err)
					continue
				} else {
					// We have successfully created a plugin from a package.
					// We save it so that we do not have to do this parsing again.
					m.persist(plugin)
				}
			}

			plugins = append(plugins, plugin)
		}
	}

	return plugins
}

// Invoke invokes an executable and runs it with the arguments given.
func (m *Manager) Invoke(executable string, args []string) error {
	shellOut := exec.Command(executable, args...)

	shellOut.Stdout = m.Stdout
	shellOut.Stderr = m.Stderr
	shellOut.Stdin = m.Stdin

	err := shellOut.Run()
	if err != nil {
		// Because we're silencing errors through Cobra, we need to print this separately.
		m.Logger.Error(err)
	}

	return err
}

// loadPluginFromPackage fills a Plugin structure from a Universe package.
// This is based on the assumption that old packages were all downloaded
// using the Universe and are thus Universe packages.
func (m *Manager) loadPluginFromPackage(plugin *Plugin) error {
	packageFilePath := filepath.Join(plugin.dir, "package.json")
	data, err := afero.ReadFile(m.Fs, packageFilePath)
	if err != nil {
		return err
	}

	pkg := &Package{}

	if err = json.Unmarshal(data, pkg); err != nil {
		return err
	}

	// We transfer the information we have from the package to the plugin.
	plugin.Name = pkg.Name
	plugin.Description = pkg.Description
	plugin.Version = pkg.Version

	// Create a handle to then get all the binaries.
	binDirHandle, err := m.Fs.Open(plugin.BinDir)
	if err != nil {
		return err
	}
	defer binDirHandle.Close()

	// Read the directory to get all the binaries.
	binaries, err := binDirHandle.Readdir(0)
	if err != nil {
		return err
	}

	executables := []*executable{}

	// Loop over the binaries to create the list of plugin executables.
	for _, binary := range binaries {
		if strings.HasPrefix(binary.Name(), "dcos-") {
			commandName := strings.TrimPrefix(binary.Name(), "dcos-")
			if runtime.GOOS == "windows" {
				commandName = strings.TrimSuffix(commandName, ".exe")
			}

			cmd := &Command{
				Name: commandName,
			}

			// We add the command information to the plugin file by shelling it out.
			cmdExe := filepath.Join(plugin.BinDir, binary.Name())
			infoCmd, err := exec.Command(cmdExe, commandName, "--info").Output()
			if err != nil {
				m.Logger.Fatal(err)
			}
			cmd.Description = strings.TrimSpace(string(infoCmd))

			// We create an executable which is what will be executed when calling a subcommand.
			exe := &executable{
				Filename: binary.Name(),
				Commands: []*Command{
					cmd,
				},
			}
			executables = append(executables, exe)
		}
	}

	plugin.Executables = executables
	return nil
}

// Persist saves a `plugin.yaml` file representing a plugin if it does not exist.
func (m *Manager) persist(plugin *Plugin) error {
	// We need an env directory for `plugin.yaml`.
	envFilePath := filepath.Join(plugin.dir, "env")
	if _, err := os.Stat(envFilePath); os.IsNotExist(err) {
		return errors.New(envFilePath + " does not exist")
	}

	// We should not overwrite `plugin.yaml`, this method should only be used
	// to create a minimal `plugin.yaml` if the user has an old plugin.
	pluginFilePath := filepath.Join(plugin.dir, "env", "plugin.yaml")
	if _, err := os.Stat(pluginFilePath); err == nil {
		return errors.New(pluginFilePath + " already exists")
	}

	// Marshal the plugin.
	pluginYAML, err := yaml.Marshal(plugin)
	if err != nil {
		return err
	}

	return afero.WriteFile(m.Fs, pluginFilePath, pluginYAML, 0644)
}
