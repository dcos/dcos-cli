package plugin_test

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/sirupsen/logrus/hooks/test"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestLoadNoPlugin(t *testing.T) {
	subcommandsDir := pluginDir(t, "no_plugins")
	logger, _ := test.NewNullLogger()

	m := plugin.Manager{
		Fs:     afero.NewMemMapFs(),
		Dir:    subcommandsDir,
		Logger: logger,
	}

	plugins := m.Plugins()
	require.Empty(t, plugins)
}

func TestLoadPluginWithBinaryOnly(t *testing.T) {
	dir := pluginDir(t, "binary_only")

	if runtime.GOOS == "windows" {
		dir = filepath.Join(dir, "windows")
	} else {
		dir = filepath.Join(dir, "unix")
	}

	logger, _ := test.NewNullLogger()

	m := plugin.Manager{
		Fs:     roFs(),
		Dir:    dir,
		Logger: logger,
	}

	plugins := m.Plugins()
	require.Equal(t, 1, len(plugins))
	plugin := plugins[0]

	require.Equal(t, "dcos-test-cli", plugin.Name)

	require.Equal(t, 1, len(plugin.Commands))
	require.Equal(t, "test", plugin.Commands[0].Name)
	require.Equal(
		t,
		filepath.Join(dir, "dcos-test-cli", "env", "bin", "dcos-test"),
		plugin.Commands[0].Path,
	)
}

func TestLoadPluginWithMalformedToml(t *testing.T) {
	dir := pluginDir(t, "malformed_toml")
	logger, _ := test.NewNullLogger()

	m := plugin.Manager{
		Fs:     roFs(),
		Dir:    dir,
		Logger: logger,
	}
	plugins := m.Plugins()

	require.Equal(t, 0, len(plugins))
}

func TestLoadPluginWithMultipleCommands(t *testing.T) {
	dir := pluginDir(t, "multiple_commands")
	logger, _ := test.NewNullLogger()

	m := plugin.Manager{
		Fs:     roFs(),
		Dir:    dir,
		Logger: logger,
	}

	plugins := m.Plugins()

	require.Equal(t, 1, len(plugins))

	require.Equal(t, 2, len(plugins[0].Commands))
	for _, cmd := range plugins[0].Commands {
		switch cmd.Name {
		case "test":
			require.Equal(
				t,
				filepath.Join(dir, "toml", "env", "bin", "dcos-test"),
				cmd.Path,
			)
		case "no-test":
			require.Equal(t, "no-test", plugins[0].Commands[1].Name)
			require.Equal(
				t,
				filepath.Join(dir, "toml", "env", "bin", "dcos-no-test"),
				cmd.Path,
			)
		default:
			t.Errorf("unexpected command '%s'", cmd.Name)
			t.FailNow()
		}
	}
}

func pluginDir(t *testing.T, name string) string {
	wd, err := os.Getwd()
	require.NoError(t, err)

	testdataDir := filepath.Join(wd, "testdata")
	return filepath.Join(testdataDir, name)
}

func roFs() afero.Fs {
	base := afero.NewOsFs()
	roBase := afero.NewReadOnlyFs(base)
	overlay := afero.NewCopyOnWriteFs(roBase, afero.NewMemMapFs())

	return overlay
}
