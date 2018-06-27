// +build windows
package plugin_test

import (
	"path/filepath"
	"testing"

	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/sirupsen/logrus/hooks/test"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoadOldPluginWindows(t *testing.T) {
	subcommandsDir := targetSubcommandDir(t, "only_old_plugin_windows")

	logger, _ := test.NewNullLogger()

	m := plugin.Manager{
		Fs:     roFs(),
		Dir:    subcommandsDir,
		Logger: logger,
	}

	plugins := m.Plugins()
	require.NotEmpty(t, plugins)

	plugin := plugins[0]

	assert.Equal(t, "old-test", plugin.Name, "plugin name does not match name found in package.json")

	pluginExists, err := afero.Exists(m.Fs, filepath.Join(subcommandsDir, "old", "env", "plugin.yaml"))
	require.NoError(t, err)

	assert.True(t, pluginExists, "plugin.yaml was not created")
}

func TestLoadNewPluginWindows(t *testing.T) {
	subcommandsDir := targetSubcommandDir(t, "only_new_plugin_windows")
	logger, _ := test.NewNullLogger()

	m := plugin.Manager{
		Fs:     roFs(),
		Dir:    subcommandsDir,
		Logger: logger,
	}

	plugins := m.Plugins()
	require.NotEmpty(t, plugins)
	plugin := plugins[0]

	assert.Equal(t, "new-test", plugin.Name)
}
