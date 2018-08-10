package login

import (
	"os"
	"runtime"
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

func TestResolvePasswordFromFile(t *testing.T) {
	fixtures := []struct {
		passwordFileContents string
		passwordFilePerm     os.FileMode
		expectedPassword     string
	}{
		{"123456", 0400, "123456"},
		{"123456\n", 0600, "123456"},
		{"123456", 0644, ""},
	}

	for _, fixture := range fixtures {
		fs := afero.NewMemMapFs()
		err := afero.WriteFile(
			fs,
			"/password.txt",
			[]byte(fixture.passwordFileContents),
			fixture.passwordFilePerm,
		)
		require.NoError(t, err)

		envLookup := func(key string) (string, bool) {
			return "", false
		}
		flags := NewFlags(fs, envLookup)
		flags.passwordFile = "/password.txt"
		err = flags.Resolve()
		if fixture.expectedPassword != "" {
			require.Equal(t, fixture.expectedPassword, flags.password)
		} else {
			// Secure files are not supported on Windows.
			if runtime.GOOS != "windows" {
				require.Error(t, err)
			}
		}
	}
}

func TestResolvePasswordFromEnvVar(t *testing.T) {
	fs := afero.NewMemMapFs()
	envLookup := func(key string) (string, bool) {
		if key == "DCOS_PASSWORD" {
			return "123456", true
		}
		return "", false
	}
	flags := NewFlags(fs, envLookup)
	require.NoError(t, flags.Resolve())
	require.Equal(t, "123456", flags.password)
}
