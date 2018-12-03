package config

import (
	"bytes"
	"testing"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/mock"
	"github.com/stretchr/testify/require"
)

func TestConfigShowEnvVar(t *testing.T) {
	var out bytes.Buffer

	env := mock.NewEnvironment()
	env.Out = &out
	env.EnvLookup = func(key string) (string, bool) {
		if key == "DCOS_TIMEOUT" {
			return "300", true
		}
		return "", false
	}

	ctx := mock.NewContext(env)
	ctx.SetCluster(config.NewCluster(config.New(config.Opts{
		EnvLookup: env.EnvLookup,
	})))
	cmd := newCmdConfigShow(ctx)
	cmd.SetArgs([]string{"core.timeout"})

	err := cmd.Execute()
	require.NoError(t, err)

	require.Equal(t, "300\n", out.String())
}
