package config

import (
	"testing"

	"github.com/pelletier/go-toml"
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

	store := NewStore(tree, StoreOpts{
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

	val := store.Get("core.dcos_url")
	require.Equal(t, "https://dcos-env.example.com", val)

	val = store.Get("core.ssl_verify")
	require.Equal(t, "true", val)

	val = store.Get("core.reporting")
	require.Equal(t, true, val)

	val = store.Get("core.timeout")
	require.EqualValues(t, 15, val)

	val = store.Get("cluster.name")
	require.Equal(t, "mr-cluster", val)
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

	store := NewStore(tree, StoreOpts{
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

	keys := store.Keys()
	expectedKeys := []string{
		"cluster.name",
		"core.dcos_url",
		"core.ssl_verify",
		"core.timeout",
		"marathon.url",
	}
	require.Equal(t, expectedKeys, keys)
}
