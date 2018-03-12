package config

import (
	"io/ioutil"
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
	require.Equal(t, "https://dcos.example.com", conf.URL())
	require.Equal(t, "token_zj8Tb0vhQw", conf.ACSToken())
	require.Equal(t, f.Name(), conf.Store().path)
}

func TestFromInvalidPath(t *testing.T) {
	_, err := FromPath("/path/to/unexisting/config/dcos.toml")
	require.Error(t, err)
}

func TestFromEmptyString(t *testing.T) {
	conf, err := FromString("")
	require.NoError(t, err)

	expectedConf := Default()

	// Remove the stores before comparing configs.
	conf.store = nil
	expectedConf.store = nil

	require.Equal(t, expectedConf, conf)
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

	require.Equal(t, "https://dcos.example.com", conf.URL())
	require.Equal(t, "token_zj8Tb0vhQw", conf.ACSToken())
	require.Equal(t, true, conf.TLS().Insecure)
	require.Equal(t, 15, conf.Timeout())
	require.Equal(t, "myuser", conf.SSHUser())
	require.Equal(t, "192.0.2.1", conf.SSHProxyHost())
	require.Equal(t, true, conf.Pagination())
	require.Equal(t, true, conf.Reporting())
	require.Equal(t, "https://mesos.example.com", conf.MesosMasterURL())
	require.Equal(t, true, conf.PromptLogin())
	require.Equal(t, "mr-cluster", conf.ClusterName())
}

func TestSave(t *testing.T) {
	conf := New()
	conf.SetURL("https://dcos.example.com")

	f, _ := afero.TempFile(fs, "/", "config")
	conf.SetPath(f.Name())

	require.NoError(t, conf.Save())

	contents, err := ioutil.ReadAll(f)
	require.NoError(t, err)

	expectedTOML := []byte(`
[core]
  dcos_url = "https://dcos.example.com"
`)
	require.Equal(t, expectedTOML, contents)
}
