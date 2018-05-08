package config

import (
	"bytes"
	"errors"
	"os/user"
	"testing"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestConfigShowEnvVar(t *testing.T) {
	var out bytes.Buffer

	env := &cli.Environment{
		Out: &out,
		Fs:  afero.NewMemMapFs(),
		EnvLookup: func(key string) (string, bool) {
			if key == "DCOS_URL" {
				return "https://dcos.example.org", true
			}
			return "", false
		},
		UserLookup: func() (*user.User, error) {
			return nil, errors.New("no user")
		},
	}

	cmd := newCmdConfigShow(cli.NewContext(env))
	cmd.SetArgs([]string{"core.dcos_url"})

	err := cmd.Execute()
	require.NoError(t, err)

	require.Equal(t, "https://dcos.example.org\n", out.String())
}
