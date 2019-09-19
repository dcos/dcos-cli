package plugin

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/sirupsen/logrus/hooks/test"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestLoadNoPlugin(t *testing.T) {
	require.Empty(t, pluginManager(t, "no_plugins").Plugins())
}

func TestLoadPluginWithBinaryOnly(t *testing.T) {
	pm := pluginManager(t, "binary_only")
	plugins := pm.Plugins()
	require.Equal(t, 1, len(plugins))
	plugin := plugins[0]

	require.Equal(t, "dcos-test-cli", plugin.Name)

	require.Equal(t, 1, len(plugin.Commands))
	require.Equal(t, "test", plugin.Commands[0].Name)
	require.Equal(
		t,
		filepath.Join(pm.pluginsDir(), "dcos-test-cli", "env", "bin", "dcos-test"),
		plugin.Commands[0].Path,
	)
}

func TestLoadPluginWithMalformedToml(t *testing.T) {
	require.Empty(t, pluginManager(t, "malformed_toml").Plugins())
}

func TestLoadPluginWithMultipleCommands(t *testing.T) {
	pm := pluginManager(t, "multiple_commands")
	plugins := pm.Plugins()

	require.Equal(t, 1, len(plugins))

	require.Equal(t, 2, len(plugins[0].Commands))
	for _, cmd := range plugins[0].Commands {
		switch cmd.Name {
		case "test":
			require.Equal(
				t,
				filepath.Join(pm.pluginsDir(), "toml", "env", "bin", "dcos-test"),
				cmd.Path,
			)
		case "no-test":
			require.Equal(t, "no-test", plugins[0].Commands[1].Name)
			require.Equal(
				t,
				filepath.Join(pm.pluginsDir(), "toml", "env", "bin", "dcos-no-test"),
				cmd.Path,
			)
		default:
			t.Errorf("unexpected command '%s'", cmd.Name)
			t.FailNow()
		}
	}

	// Command names should be sorted.
	require.Equal(t, []string{"no-test", "test"}, plugins[0].CommandNames())
}

func pluginManager(t *testing.T, name string) *Manager {
	baseFs := afero.NewOsFs()
	baseRoFs := afero.NewReadOnlyFs(baseFs)
	fs := afero.NewCopyOnWriteFs(baseRoFs, afero.NewMemMapFs())

	logger, _ := test.NewNullLogger()

	wd, err := os.Getwd()
	require.NoError(t, err)

	clusterDir := filepath.Join(wd, "testdata", name)

	conf := config.New(config.Opts{
		Fs: fs,
	})
	conf.SetPath(filepath.Join(clusterDir, "dcos.toml"))

	pluginManager := NewManager(fs, logger)
	pluginManager.SetCluster(config.NewCluster(conf))
	return pluginManager
}
