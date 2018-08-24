package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestCurrent(t *testing.T) {
	wd, err := os.Getwd()
	require.NoError(t, err)

	fixturesDir := filepath.Join(wd, "testdata")

	fixtures := []struct {
		name       string
		envLookup  func(key string) (val string, ok bool)
		shouldFail bool
	}{
		{"conflicting_.dcos_file", nil, true},
		{"multi_config_with_none_attached", nil, true},
		{"multiple_config_attached", nil, true},
		{"conflicting_clusters_file", nil, true},
		{"single_config_attached", nil, false},
		{"single_config_unattached", nil, false},
		{"multi_config_with_one_attached", nil, false},
		{"multi_config_with_none_attached", func(key string) (val string, ok bool) {
			if key == "DCOS_CLUSTER" {
				return "97193161-f7f1-2295-2514-a6b3918043b6", true
			}
			return
		}, false},
		{"multi_config_with_none_attached", func(key string) (val string, ok bool) {
			if key == "DCOS_CLUSTER" {
				return "multi_config_with_none_attached", true
			}
			return
		}, false},
		{"multi_config_with_none_attached", func(key string) (val string, ok bool) {
			if key == "DCOS_CLUSTER" {
				return "multi_config_with", true
			}
			return
		}, true},
	}

	for _, fixture := range fixtures {
		dcosDir := filepath.Join(fixturesDir, fixture.name, ".dcos")
		manager := NewManager(ManagerOpts{
			Dir:       dcosDir,
			EnvLookup: fixture.envLookup,
		})

		t.Run(fixture.name, func(t *testing.T) {
			conf, err := manager.Current()
			if fixture.shouldFail {
				require.Error(t, err)
			} else {
				require.NoError(t, err)
				require.Equal(t, fixture.name, conf.Get("cluster.name").(string))
			}
		})
	}
}

func TestFind(t *testing.T) {
	wd, err := os.Getwd()
	require.NoError(t, err)

	fixturesDir := filepath.Join(wd, "testdata")

	fixtures := []struct {
		name       string
		search     string
		shouldFail bool
	}{
		{"multi_config_with_same_name", "multi_config_with_same_name", true},
		{"multi_config_with_same_name", "multi", true},
		{"multi_config_with_same_name", "97193161-f7f1-2295-2514-a6b3918043b6", false},
		{"multi_config_with_same_name", "97193161", false},
	}

	for _, fixture := range fixtures {
		dcosDir := filepath.Join(fixturesDir, fixture.name, ".dcos")
		manager := NewManager(ManagerOpts{
			Dir: dcosDir,
		})

		t.Run(fixture.name, func(t *testing.T) {
			conf, err := manager.Find(fixture.search, false)
			if fixture.shouldFail {
				require.Error(t, err)
			} else {
				require.NoError(t, err)
				require.Equal(t, fixture.name, conf.Get("cluster.name").(string))
				require.Equal(t, "https://success.example.com", conf.Get("core.dcos_url").(string))
			}
		})
	}
}

func TestAttach(t *testing.T) {
	fs := afero.NewMemMapFs()
	clusterID := "97193161-f7f1-2295-2514-a6b3918043b6"
	fs.Create(filepath.Join(".dcos", "clusters", clusterID, "dcos.toml"))

	manager := NewManager(ManagerOpts{
		Dir: ".dcos",
		Fs:  fs,
	})

	conf, err := manager.Find(clusterID, true)
	require.NoError(t, err)

	attachedFilePath := manager.attachedFilePath(conf)

	require.False(t, manager.fileExists(attachedFilePath))
	require.NoError(t, manager.Attach(conf))
	require.True(t, manager.fileExists(attachedFilePath))
}
