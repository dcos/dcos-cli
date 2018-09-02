package cli

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestParseGlobalFlags(t *testing.T) {
	fixtures := []struct {
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

	for _, fixture := range fixtures {
		var gf GlobalFlags
		args := gf.Parse(fixture.args)
		require.Equal(t, fixture.flags, gf)
		require.Equal(t, fixture.argsWoFlags, args)
	}
}
