package login

import (
	"os"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/spf13/afero"
)

func TestResolveUsernameFromEnvVar(t *testing.T) {
	fs := afero.NewMemMapFs()
	envLookup := func(key string) (string, bool) {
		if key == "DCOS_USERNAME" {
			return "alice", true
		}
		return "", false
	}
	flags := NewFlags(fs, envLookup)
	require.NoError(t, flags.Resolve())
	require.Equal(t, "alice", flags.username)
}
