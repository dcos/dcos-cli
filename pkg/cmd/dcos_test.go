package cmd

import (
	"bytes"
	"testing"

	"github.com/dcos/dcos-cli/pkg/mock"
	"github.com/stretchr/testify/require"
)

func TestDCOSHelp(t *testing.T) {
	var out bytes.Buffer
	env := mock.NewEnvironment()
	env.Out = &out

	ctx := mock.NewContext(env)

	cmd := NewDCOSCommand(ctx)
	cmd.InitDefaultHelpCmd()
	cmd.SetOutput(env.Out)

	require.NoError(t, cmd.Help())

	var expectedHelp = `Usage:
    dcos [command]

Commands:
    auth
        Authenticate to DC/OS cluster
    cluster
        Manage your DC/OS clusters
    config
        Manage the DC/OS configuration file
    help
        Help about any command
    plugin
        Manage CLI plugins

Options:
    --version
        Print version information
    -v, -vv
        Output verbosity (verbose or very verbose)
    -h, --help
        Show usage help

Use "dcos [command] --help" for more information about a command.
`

	require.Equal(t, expectedHelp, out.String())
}

func TestCmdConfigEnvKey(t *testing.T) {
	require.Equal(t, "DCOS_HELLO_WORLD", cmdConfigEnvKey("hello", "world"))
	require.Equal(t, "DCOS_HELLO_WORLD_FOO", cmdConfigEnvKey("hello-world", "foo"))
	require.Equal(t, "DCOS_HELLO_AROUND_THE_WORLD", cmdConfigEnvKey("hello", "around_the_world"))
}
