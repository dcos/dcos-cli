package cli

import (
	"os"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestRelativeDCOSDir(t *testing.T) {
	currentDir, err := os.Getwd()
	require.NoError(t, err)

	dcosDir, err := NewContext(&Environment{
		EnvLookup: func(key string) (string, bool) {
			if key == "DCOS_DIR" {
				return ".", true
			}
			return "", false
		},
	}).DCOSDir()
	require.NoError(t, err)
	require.Equal(t, currentDir, dcosDir)
}
