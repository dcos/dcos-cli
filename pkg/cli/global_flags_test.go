package cli

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestParseGlobalFlags(t *testing.T) {
	testCases := []struct {
		args        []string
		argsWoFlags []string
		flags       GlobalFlags
	}{
		{[]string{}, []string{}, GlobalFlags{}},
		{[]string{"--log-level"}, []string{}, GlobalFlags{}},
		{[]string{"--log-level="}, []string{}, GlobalFlags{}},
		{
			[]string{"--version"},
			[]string{},
			GlobalFlags{
				Version: true,
			},
		},
		{
			[]string{"--log-level", "debug", "--debug", "cluster"},
			[]string{"cluster"},
			GlobalFlags{
				LogLevel: "debug",
				Debug:    true,
			},
		},
		{
			[]string{"--log-level=info", "-vvv"},
			[]string{},
			GlobalFlags{
				LogLevel:  "info",
				Verbosity: 2,
			},
		},
		{
			[]string{"--log-level=warning", "cluster", "-vv"},
			[]string{"cluster", "-vv"},
			GlobalFlags{
				LogLevel: "warning",
			},
		},
	}

	for _, tc := range testCases {
		var gf GlobalFlags
		args := gf.Parse(tc.args)
		require.Equal(t, tc.flags, gf)
		require.Equal(t, tc.argsWoFlags, args)
	}
}
