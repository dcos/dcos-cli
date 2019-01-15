package cli

import (
	"bytes"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestDeprecation(t *testing.T) {
	var out bytes.Buffer
	deprecated := NewDeprecationHelper(
		DeprecationHelperOpts{
			Output: &out,
			EnvLookup: func(key string) (string, bool) {
				return "", false
			},
		},
	)
	require.NoError(t, deprecated("This is not fatal"))
	require.Equal(t, out.String(), "This is not fatal\n")
}

func TestFailOnDeprecation(t *testing.T) {
	var out bytes.Buffer

	deprecated := NewDeprecationHelper(
		DeprecationHelperOpts{
			Output: &out,
			EnvLookup: func(key string) (string, bool) {
				if key == "DCOS_CLI_FAIL_ON_DEPRECATION" {
					return "1", true
				}
				return "", false
			},
		},
	)
	require.Error(t, deprecated("This is fatal"))
	require.Equal(t, out.String(), "This is fatal\n")
}
