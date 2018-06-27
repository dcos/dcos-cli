package plugin_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/sirupsen/logrus/hooks/test"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/dcos/dcos-cli/pkg/plugin"
)

func TestLoadNoPlugin(t *testing.T) {
	subcommandsDir := targetSubcommandDir(t, "no_plugins")

	m := plugin.Manager{
		Fs:  afero.NewMemMapFs(),
		Dir: subcommandsDir,
	}

	plugins := m.Plugins()
	require.Empty(t, plugins)
}

func TestLoadNewPlugin(t *testing.T) {
	subcommandsDir := targetSubcommandDir(t, "only_new_plugin")
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

func TestLoadOldPlugin(t *testing.T) {
	subcommandsDir := targetSubcommandDir(t, "only_old_plugin")

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

func TestIgnoreMalformedYaml(t *testing.T) {
	dir := targetSubcommandDir(t, "malformed_yaml")
	logger, _ := test.NewNullLogger()

	m := plugin.Manager{
		Fs:     roFs(),
		Dir:    dir,
		Logger: logger,
	}
	plugins := m.Plugins()

	assert.Empty(t, plugins)
}

func targetSubcommandDir(t *testing.T, name string) string {
	wd, err := os.Getwd()
	require.NoError(t, err)

	return filepath.Join(wd, "testdata", name)
}

func roFs() afero.Fs {
	base := afero.NewOsFs()
	roBase := afero.NewReadOnlyFs(base)
	overlay := afero.NewCopyOnWriteFs(roBase, afero.NewMemMapFs())

	return overlay
}
