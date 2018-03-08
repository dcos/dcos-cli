package config

import (
	"testing"

	"github.com/pelletier/go-toml"
	"github.com/stretchr/testify/require"
)

func TestFromStore(t *testing.T) {
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

	conf := fromStore(NewStore(tree, StoreOpts{}))
	require.NoError(t, err)

	require.Equal(t, "https://dcos.example.com", conf.URL)
	require.Equal(t, true, conf.TLS.Insecure)
	require.Equal(t, 15, conf.Timeout)
	require.Equal(t, true, conf.Reporting)
	require.Equal(t, "mr-cluster", conf.ClusterName)
}
