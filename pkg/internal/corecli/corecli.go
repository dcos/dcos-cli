package corecli

import (
	"os"
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/fsutil"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/pelletier/go-toml"
	"github.com/spf13/afero"
)

// TempPlugin will read the bundled corecli into a memmapfs and return a fake plugin from that data.
func TempPlugin() (*plugin.Plugin, error) {
	tempFs := afero.NewMemMapFs()

	pluginFilePath, err := extractPlugin(tempFs)
	if err != nil {
		return nil, err
	}

	err = fsutil.Unzip(tempFs, pluginFilePath, "/dcos-core-cli")
	if err != nil {
		return nil, err
	}

	pluginTOMLFilePath := filepath.Join("/dcos-core-cli", "plugin.toml")
	data, err := afero.ReadFile(tempFs, pluginTOMLFilePath)
	if err != nil {
		return nil, err
	}

	plugin := &plugin.Plugin{}
	err = toml.Unmarshal(data, plugin)
	if err != nil {
		return nil, err
	}
	return plugin, nil
}

func extractPlugin(fs afero.Fs) (string, error) {
	pluginData, err := Asset("core.zip")
	if err != nil {
		return "", err
	}

	pluginFile, err := afero.TempFile(fs, os.TempDir(), "dcos-core-cli.zip")
	if err != nil {
		return "", err
	}
	defer pluginFile.Close()

	_, err = pluginFile.Write(pluginData)
	if err != nil {
		return "", err
	}

	return pluginFile.Name(), nil
}

// InstallPlugin installs the core plugin bundled with the CLI.
func InstallPlugin(fs afero.Fs, pluginManager *plugin.Manager, deprecated func(msg string) error) error {
	if err := deprecated(`Extracting "dcos-core-cli"...
This setup is deprecated, see https://docs.mesosphere.com/1.13/cli/plugins/ for more information.`); err != nil {
		return err
	}

	pluginFilePath, err := extractPlugin(fs)
	if err != nil {
		return err
	}
	defer fs.Remove(pluginFilePath)
	err = pluginManager.Install(pluginFilePath, &plugin.InstallOpts{})
	if _, ok := err.(plugin.ExistError); ok {
		// While it was not there at the beginning of the process execution, it is possible that the
		// core plugin was either installed or auto-extracted by another concurrent CLI command invocation.
		// We don't fail here as the core plugin is now installed and can be invoked safely.
		//
		// See https://jira.mesosphere.com/browse/DCOS_OSS-4843
		return nil
	}
	return err
}
