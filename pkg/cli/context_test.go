package cli

import (
	"bytes"
	"os"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestRelativeDCOSDir(t *testing.T) {
	currentDir, err := os.Getwd()
	require.NoError(t, err)

	dcosDir, err := NewContext(&Environment{
		EnvLookup: func(key string) (string, bool) {
			if key == EnvDCOSDir {
				return ".", true
			}
			return "", false
		},
	}).DCOSDir()
	require.NoError(t, err)
	require.Equal(t, currentDir, dcosDir)
}

func TestDeprecation(t *testing.T) {
	var out bytes.Buffer

	err := NewContext(&Environment{
		ErrOut: &out,
		EnvLookup: func(key string) (string, bool) {
			return "", false
		},
	}).Deprecated("This is not fatal")

	require.NoError(t, err)
	require.Equal(t, out.String(), "This is not fatal\n")
}

func TestFatalDeprecation(t *testing.T) {
	var out bytes.Buffer

	err := NewContext(&Environment{
		ErrOut: &out,
		EnvLookup: func(key string) (string, bool) {
			if key == EnvStrictDeprecations {
				return "1", true
			}
			return "", false
		},
	}).Deprecated("This is fatal")

	require.Error(t, err)
	require.Equal(t, out.String(), "This is fatal\n")
}
