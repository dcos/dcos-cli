package plugin

import (
	"fmt"
	"io/ioutil"
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
	yaml "gopkg.in/yaml.v2"
)

// Plugins returns all plugins associated with the current cluster.
func Plugins(ctx *cli.Context) []*Plugin {
	plugins := []*Plugin{}

	pluginsDir := pluginsDir(ctx)

	pluginsDirHandle, err := ctx.Fs().Open(pluginsDir)
	if err != nil {
		return []*Plugin{}
	}
	defer pluginsDirHandle.Close()

	pluginsDirInfo, err := pluginsDirHandle.Readdir(-1)
	if err != nil {
		return plugins
	}

	for _, pluginDirInfo := range pluginsDirInfo {
		if pluginDirInfo.IsDir() {
			definitionFilePath := filepath.Join(pluginsDir, pluginDirInfo.Name(), "plugin.yaml")

			plugin := &Plugin{}

			// set plugin directories
			plugin.pluginDir = filepath.Join(pluginsDir, pluginDirInfo.Name())
			plugin.binDir = filepath.Join(pluginsDir, pluginDirInfo.Name(), "/bin")

			data, err := ioutil.ReadFile(definitionFilePath)
			if err == nil {
				if err = yaml.Unmarshal(data, &plugin); err != nil {
					fmt.Println(err)
					continue
				}
			} else {
				// TODO: if there's no plugin yaml, it's possibly an old style command
				fmt.Println(err)
				continue
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

func pluginsDir(ctx *cli.Context) string {
	config, err := ctx.ConfigManager().Current()
	if err != nil {
		//return nil, err
		// TODO: handle this error
		return ""
	}

	configHome := filepath.Dir(config.Path())
	dir := filepath.Join(configHome, "subcommands")

	return dir
}
