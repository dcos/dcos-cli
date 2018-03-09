package config

import (
	"os"
	"testing"

	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestMain(m *testing.M) {
	fs = afero.NewMemMapFs()

	os.Exit(m.Run())
}

func TestFromPath(t *testing.T) {
	cfg := `
[core]
dcos_url = "https://dcos.example.com"
dcos_acs_token = "token_zj8Tb0vhQw"
`
	f, _ := afero.TempFile(fs, "/", "config")
	f.Write([]byte(cfg))

	conf, err := FromPath(f.Name())
	require.NoError(t, err)
	require.Equal(t, "https://dcos.example.com", conf.URL)
	require.Equal(t, "token_zj8Tb0vhQw", conf.ACSToken)
}

func TestFromEmptyString(t *testing.T) {
	conf, err := FromString("")
	require.NoError(t, err)

	// Remove the store before comparing with the default config.
	require.NotNil(t, conf.Store())
	conf.store = nil

	require.Equal(t, DefaultConfig(), conf)
}

func TestFromFullConfigString(t *testing.T) {
	conf, err := FromString(`
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
`)
	require.NoError(t, err)

	require.Equal(t, "https://dcos.example.com", conf.URL)
	require.Equal(t, "token_zj8Tb0vhQw", conf.ACSToken)
	require.Equal(t, true, conf.TLS.Insecure)
	require.Equal(t, 15, conf.Timeout)
	require.Equal(t, "myuser", conf.SSHUser)
	require.Equal(t, "192.0.2.1", conf.SSHProxyIP)
	require.Equal(t, true, conf.Pagination)
	require.Equal(t, true, conf.Reporting)
	require.Equal(t, "https://mesos.example.com", conf.MesosMasterURL)
	require.Equal(t, true, conf.PrompLogin)
	require.Equal(t, "mr-cluster", conf.ClusterName)
}
