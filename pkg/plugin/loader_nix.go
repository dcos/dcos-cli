// +build !windows

package plugin

import (
	"io/ioutil"
	"path/filepath"
	"strings"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
	yaml "gopkg.in/yaml.v2"
)

// Plugins returns all plugins associated with the current cluster.
func Plugins(ctx *cli.Context) []*Plugin {
	plugins := []*Plugin{}

	pluginsDir, err := pluginsDir(ctx)
	if err != nil {
		// This probably means there is no currently attached cluster thus no plugins to load.
		return plugins
	}

	pluginsDirHandle, err := ctx.Fs().Open(pluginsDir)
	if err != nil {
		return plugins
	}
	defer pluginsDirHandle.Close()

	pluginsDirInfo, err := pluginsDirHandle.Readdir(-1)
	if err != nil {
		return plugins
	}

	for _, pluginDirInfo := range pluginsDirInfo {
		if pluginDirInfo.IsDir() {
			plugin := &Plugin{}

			// set plugin directories
			plugin.pluginDir = filepath.Join(pluginsDir, pluginDirInfo.Name())
			plugin.binDir = filepath.Join(plugin.pluginDir, "bin")

			definitionFilePath := filepath.Join(plugin.pluginDir, "plugin.yaml")
			data, err := ioutil.ReadFile(definitionFilePath)
			// Since we don't want to have the CLI fail if a single plugin is malformed. It will log the error
			// but otherwise continue.
			if err == nil {
				if err = yaml.Unmarshal(data, plugin); err != nil {
					ctx.Logger().Warning(err)
					continue
				}
			} else {
				// plugin.yaml not found, try loading this as an old-style plugin
				if err = oldPlugin(ctx, plugin); err != nil {
					ctx.Logger().Warning(err)
					continue
				}
			}

			plugins = append(plugins, plugin)
		}
	}

	return plugins
}

// CreateCommands will create cobra commands from the given plugin list
func CreateCommands(ctx *cli.Context, plugins []*Plugin) []*cobra.Command {
	commands := []*cobra.Command{}

	for _, p := range plugins {
		commands = append(commands, p.IntoCommands(ctx)...)
	}

	return commands
}

func oldPlugin(ctx *cli.Context, plugin *Plugin) error {
	dir := plugin.pluginDir
	plugin.binDir = filepath.Join(dir, "env", "bin")

	binDirHandle, err := ctx.Fs().Open(plugin.binDir)
	if err != nil {
		return err
	}
	defer binDirHandle.Close()

	binaries, err := binDirHandle.Readdir(-1)
	if err != nil {
		return err
	}

	executables := []*Executable{}
	for _, binary := range binaries {
		if strings.HasPrefix(binary.Name(), "dcos-") {
			commandName := strings.TrimLeft(binary.Name(), "dcos-")
			cmd := &Command{
				Name: commandName,
			}

			exe := &Executable{
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

func pluginsDir(ctx *cli.Context) (string, error) {
	config, err := ctx.ConfigManager().Current()
	if err != nil {
		return "", err
	}

	configHome := filepath.Dir(config.Path())
	dir := filepath.Join(configHome, "subcommands")

	return dir, nil
}
