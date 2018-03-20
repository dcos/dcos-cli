package config

import (
	"testing"

	"github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
	"github.com/xeipuuv/gojsonschema"
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

	require.Equal(t, "https://dcos-env.example.com", store.Get(keyURL))
	require.Equal(t, "true", store.Get(keyTLS))
	require.Equal(t, true, store.Get(keyReporting))
	require.EqualValues(t, 15, store.Get(keyTimeout))
	require.Equal(t, "mr-cluster", store.Get(keyClusterName))

	// Getting a TOML subtree should return nil.
	require.Equal(t, nil, store.Get("core"))
}

func TestStoreSetAndUnset(t *testing.T) {
	store := NewStore(StoreOpts{})

	store.Set(keyURL, "https://dcos.example.com")
	store.Set(keyTimeout, "30")
	store.Set(keyReporting, "1")

	// Test that we only accept keys associated to TOML leaves.
	// Assertions below will make sure store values are still present.
	store.Unset("core")
	store.Unset(keyURL + ".unknown_nested_key")

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

func TestPersistWithoutPath(t *testing.T) {
	store := NewStore(StoreOpts{})
	require.Error(t, store.Persist())
}

func TestPersist(t *testing.T) {
	store := NewStore(StoreOpts{})

	f, _ := afero.TempFile(fs, "/", "config")
	store.SetPath(f.Name())

	require.NoError(t, store.Persist())
}

func TestNormalizeTimeout(t *testing.T) {
	store := NewStore(StoreOpts{})

	val, err := store.normalize(keyTimeout, 30)
	require.NoError(t, err)
	require.EqualValues(t, val, 30)

	val, err = store.normalize(keyTimeout, "30")
	require.NoError(t, err)
	require.EqualValues(t, val, 30)

	val, err = store.normalize(keyTimeout, "not-a-timeout")
	require.Error(t, err)
	require.EqualValues(t, val, 0)
}

func TestNormalizeWithInvalidKey(t *testing.T) {
	store := NewStore(StoreOpts{})

	val, err := store.normalize("section_without_config", "whatever")
	require.Equal(t, ErrInvalidKey, err)
	require.Equal(t, nil, val)
}

func TestNormalizeAgainstJSONSchema(t *testing.T) {
	// A store with a JSON schema for the "marathon" section.
	schema, err := gojsonschema.NewSchema(gojsonschema.NewStringLoader(`{
		"$schema": "http://json-schema.org/schema#",
		"type": "object",
		"properties": {
			"url": {
				"type": "string",
				"format": "uri",
				"title": "Marathon base URL",
				"description": "Base URL for talking to Marathon. It overwrites the value specified in core.dcos_url",
				"default": "http://localhost:8080"
			}
		},
		"additionalProperties": false
	}`))
	require.NoError(t, err)

	store := NewStore(StoreOpts{
		JSONSchemas: map[string]*gojsonschema.Schema{
			"marathon": schema,
		},
	})

	val, err := store.normalize("marathon.url", "https://example.com/marathon")
	require.NoError(t, err)
	require.Equal(t, val, "https://example.com/marathon")

	invalidMarathonURLs := []interface{}{
		123,
		"example.com",
		"This is not a valid Marathon URL either.",
	}
	for _, invalidMarathonURL := range invalidMarathonURLs {
		val, err = store.normalize("marathon.url", invalidMarathonURL)
		require.Error(t, err)
		require.Nil(t, val, nil)
	}

	val, err = store.normalize("marathon.unknown_key", "dummy")
	require.Error(t, err)
	require.Equal(t, val, nil)

	val, err = store.normalize("unknown_section.unknown_key", "random_value")
	require.NoError(t, err)
	require.Equal(t, val, "random_value")
}
