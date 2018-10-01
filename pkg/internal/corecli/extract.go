package corecli

import (
	"github.com/dcos/dcos-cli/pkg/fsutil"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"path/filepath"
)

// TempPlugin will read the bundled corecli into a memmapfs and return a fake plugin from that data.
func TempPlugin() (*plugin.Plugin, error) {
	tempFs := afero.NewMemMapFs()
	plugin := &plugin.Plugin{}

	bundle, err := extractPlugin(tempFs)
	if err != nil {
		return nil, err
	}

	err = fsutil.Unzip(tempFs, bundle, "/dcos-core-cli")
	if err != nil {
		return nil, err
	}

	pluginFilePath := filepath.Join("/dcos-core-cli", "plugin.toml")
	data, err := afero.ReadFile(tempFs, pluginFilePath)
	if err != nil {
		return nil, err
	}
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

	if err != nil {
		return "", err
	}

	pluginFile, err := afero.TempFile(fs, "/", "dcos-core-cli.zip")
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
