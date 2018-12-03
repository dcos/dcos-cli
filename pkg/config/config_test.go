package config

import (
	"io/ioutil"
	"path/filepath"
	"strings"
	"testing"

	"github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestLoadPath(t *testing.T) {
	fs := afero.NewMemMapFs()

	cfg := `
[core]
dcos_url = "https://dcos.example.com"
dcos_acs_token = "token_zj8Tb0vhQw"
`
	f, _ := afero.TempFile(fs, "/", "config")
	f.Write([]byte(cfg))

	store := New(Opts{
		Fs: fs,
	})
	err := store.LoadPath(f.Name())
	require.NoError(t, err)
	require.Equal(t, "https://dcos.example.com", store.Get(keyURL).(string))
	require.Equal(t, "token_zj8Tb0vhQw", store.Get(keyACSToken).(string))
	require.Equal(t, f.Name(), store.Path())
}

func TestLoadJsonPath(t *testing.T) {
	fs := afero.NewMemMapFs()

	cfg := `{
		"core": { "dcos_url": "https://toml.example.com" }
}`
	f, _ := afero.TempFile(fs, "/", "config")
	f.Write([]byte(cfg))

	store := New(Opts{
		Fs: fs,
	})
	err := store.LoadPath(f.Name())
	require.Error(t, err)
}

func TestLoadInvalidPath(t *testing.T) {
	// Memory FS can't be used here as it creates missing parent directories with O_CREATE.
	fs := afero.NewOsFs()
	store := New(Opts{Fs: fs})

	tempDir, err := afero.TempDir(store.Fs(), "", "dcos_cli_tests")
	require.NoError(t, err)
	defer fs.Remove(tempDir)

	// Try to load a config path with a missing paraent directory.
	err = store.LoadPath(filepath.Join(tempDir, "unexisting_dir", "dcos.toml"))
	require.Error(t, err)
}

func TestLoadEmptyString(t *testing.T) {
	store := New(Opts{
		Fs: afero.NewMemMapFs(),
	})
	err := store.LoadReader(strings.NewReader(""))
	require.NoError(t, err)

	require.Equal(t, make(map[string]interface{}), store.tree.ToMap())
}

func TestLoadFullConfigString(t *testing.T) {
	store := Empty()
	err := store.LoadReader(strings.NewReader(`
[core]

dcos_url = "https://dcos.example.com"
dcos_acs_token = "token_zj8Tb0vhQw"
ssl_verify = "/path/to/dcos_ca.crt"
timeout = 15
ssh_user = "myuser"
ssh_proxy_ip = "192.0.2.1"
pagination = true
reporting = true
mesos_master_url = "https://mesos.example.com"
prompt_login = true

[cluster]

name = "mr-cluster"
`))

	require.NoError(t, err)

	require.Equal(t, "https://dcos.example.com", store.Get(keyURL).(string))
	require.Equal(t, "token_zj8Tb0vhQw", store.Get(keyACSToken).(string))
	require.Equal(t, "/path/to/dcos_ca.crt", store.Get(keyTLS).(string))
	require.EqualValues(t, 15, store.Get(keyTimeout).(int64))
	require.Equal(t, "myuser", store.Get(keySSHUser).(string))
	require.Equal(t, "192.0.2.1", store.Get(keySSHProxyHost).(string))
	require.Equal(t, true, store.Get(keyPagination).(bool))
	require.Equal(t, true, store.Get(keyReporting).(bool))
	require.Equal(t, "https://mesos.example.com", store.Get(keyMesosMasterURL).(string))
	require.Equal(t, true, store.Get(keyPrompLogin).(bool))
	require.Equal(t, "mr-cluster", store.Get(keyClusterName).(string))
}

func TestGet(t *testing.T) {
	treeMap := map[string]interface{}{
		"core": map[string]interface{}{
			"dcos_url":   "https://dcos.example.com",
			"ssl_verify": "false",
			"timeout":    15,
			"reporting":  true,
		},
		"cluster": map[string]interface{}{
			"name": "mr-cluster",
		},
	}

	tree, err := toml.TreeFromMap(treeMap)
	require.NoError(t, err)

	store := New(Opts{
		EnvLookup: func(key string) (string, bool) {
			switch key {
			case "DCOS_URL":
				return "https://dcos-env.example.com", true
			case "DCOS_SSL_VERIFY":
				return "true", true
			case "DCOS_CLUSTER_NAME":
				return "dummy", true
			}
			return "", false
		},
	})
	store.LoadTree(tree)

	val := store.Get(keyURL)
	require.Equal(t, "https://dcos.example.com", val)

	val = store.Get(keyTLS)
	require.Equal(t, "true", val)

	val = store.Get(keyReporting)
	require.Equal(t, true, val)

	val = store.Get(keyTimeout)
	require.EqualValues(t, 15, val)

	val = store.Get(keyClusterName)
	require.Equal(t, "mr-cluster", val)
}

func TestSetAndUnset(t *testing.T) {
	store := New(Opts{})

	store.Set(keyURL, "https://dcos.example.com")
	store.Set(keyTimeout, "30")
	store.Set(keyReporting, "1")

	require.Equal(t, nil, store.Get("core"))
	store.Unset("core")
	store.Unset("core.dcos_url.unexisting")

	require.Equal(t, "https://dcos.example.com", store.Get(keyURL))
	require.Equal(t, true, store.Get(keyReporting))
	require.EqualValues(t, 30, store.Get(keyTimeout))

	store.Unset(keyURL)
	require.Nil(t, store.Get(keyURL))
}

func TestKeys(t *testing.T) {
	treeMap := map[string]interface{}{
		"core": map[string]interface{}{
			"dcos_url": "https://dcos.example.com",
			"timeout":  15,
		},
		"cluster": map[string]interface{}{
			"name": "mr-cluster",
		},
		"marathon": map[string]interface{}{
			"url": "https://marathon.example.com",
		},
	}

	tree, err := toml.TreeFromMap(treeMap)
	require.NoError(t, err)

	store := New(Opts{
		EnvLookup: func(key string) (string, bool) {
			switch key {
			case "DCOS_URL":
				return "https://dcos-env.example.com", true
			case "DCOS_SSL_VERIFY":
				return "true", true
			}
			return "", false
		},
	})
	store.LoadTree(tree)

	expectedKeys := []string{
		"cluster.name",
		"core.dcos_url",
		"core.ssl_verify",
		"core.timeout",
		"marathon.url",
	}
	require.Equal(t, expectedKeys, store.Keys())
}

func TestPersistWithoutPath(t *testing.T) {
	store := New(Opts{})
	require.Equal(t, ErrNoConfigPath, store.Persist())
}

func TestPersist(t *testing.T) {
	fs := afero.NewMemMapFs()
	store := New(Opts{
		Fs: fs,
	})
	store.Set(keyURL, "https://dcos.example.com")

	f, _ := afero.TempFile(fs, "/", "config")
	store.SetPath(f.Name())

	require.NoError(t, store.Persist())

	contents, err := ioutil.ReadAll(f)
	require.NoError(t, err)

	expectedTOML := []byte(`
[core]
  dcos_url = "https://dcos.example.com"
`)
	require.Equal(t, expectedTOML, contents)
}
