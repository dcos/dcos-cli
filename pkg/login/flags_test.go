package login

import (
	"os"
	"runtime"
	"testing"

	"github.com/sirupsen/logrus"
	logrustest "github.com/sirupsen/logrus/hooks/test"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestResolveUsernameFromEnvVar(t *testing.T) {
	fs := afero.NewMemMapFs()
	envLookup := func(key string) (string, bool) {
		if key == "DCOS_USERNAME" {
			return "alice", true
		}
		return "", false
	}
	logger, _ := logrustest.NewNullLogger()
	flags := NewFlags(fs, envLookup, logger)
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
		logger, _ := logrustest.NewNullLogger()
		flags := NewFlags(fs, envLookup, logger)
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
	logger, hook := logrustest.NewNullLogger()
	flags := NewFlags(fs, envLookup, logger)
	require.NoError(t, flags.Resolve())
	require.Equal(t, "123456", flags.password)
	require.Equal(t, 1, len(hook.AllEntries()))
	entry := hook.LastEntry()
	require.Equal(t, logrus.InfoLevel, entry.Level)
	require.Equal(t, "Read password from environment.", entry.Message)
}
