package config

import (
	"testing"

	"github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestStoreGet(t *testing.T) {
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

	store := NewStore(StoreOpts{
		Tree: tree,
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

	val := store.Get(keyURL)
	require.Equal(t, "https://dcos-env.example.com", val)

	val = store.Get(keyTLS)
	require.Equal(t, "true", val)

	val = store.Get(keyReporting)
	require.Equal(t, true, val)

	val = store.Get(keyTimeout)
	require.EqualValues(t, 15, val)

	val = store.Get(keyClusterName)
	require.Equal(t, "mr-cluster", val)
}

func TestStoreSetAndUnset(t *testing.T) {
	store := NewStore(StoreOpts{})

	store.Set(keyURL, "https://dcos.example.com")
	store.Set(keyTimeout, "30")
	store.Set(keyReporting, "1")

	require.Equal(t, "https://dcos.example.com", store.Get(keyURL))
	require.Equal(t, true, store.Get(keyReporting))
	require.EqualValues(t, 30, store.Get(keyTimeout))

	store.Unset(keyURL)
	require.Nil(t, store.Get(keyURL))
}

func TestStoreKeys(t *testing.T) {
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

	store := NewStore(StoreOpts{
		Tree: tree,
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
	store := NewStore(StoreOpts{})
	require.Equal(t, ErrNoStorePath, store.Persist())
}

func TestPersist(t *testing.T) {
	store := NewStore(StoreOpts{})

	f, _ := afero.TempFile(fs, "/", "config")
	store.SetPath(f.Name())

	require.NoError(t, store.Persist())
}
