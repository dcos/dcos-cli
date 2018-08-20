package main

import (
	"testing"

	"github.com/dcos/dcos-cli/pkg/mock"
	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/require"
)

func TestRunWithoutVerbosity(t *testing.T) {
	ctx := mock.NewContext(nil)
	require.NoError(t, run(ctx, []string{"dcos"}))

	require.Equal(t, logrus.ErrorLevel, ctx.Logger().Level)
}

func TestRunWithInfoVerbosity(t *testing.T) {
	ctx := mock.NewContext(nil)
	require.NoError(t, run(ctx, []string{"dcos", "-v"}))

	require.Equal(t, logrus.InfoLevel, ctx.Logger().Level)
}

func TestRunWithDebugVerbosity(t *testing.T) {
	ctx := mock.NewContext(nil)
	require.NoError(t, run(ctx, []string{"dcos", "-vv"}))

	require.Equal(t, logrus.DebugLevel, ctx.Logger().Level)
}

func TestRunWithDebugFlag(t *testing.T) {
	ctx := mock.NewContext(nil)
	require.NoError(t, run(ctx, []string{"dcos", "--debug"}))

	require.Equal(t, logrus.DebugLevel, ctx.Logger().Level)
}

func TestRunWithLogLevel(t *testing.T) {
	ctx := mock.NewContext(nil)

	logLevelFlagValues := map[string]logrus.Level{
		"debug":    logrus.DebugLevel,
		"info":     logrus.InfoLevel,
		"warning":  logrus.InfoLevel,
		"error":    logrus.ErrorLevel,
		"critical": logrus.ErrorLevel,
	}

	for flagValue, logLevel := range logLevelFlagValues {
		require.NoError(t, run(ctx, []string{"dcos", "--log-level=" + flagValue}))
		require.Equal(t, logLevel, ctx.Logger().Level)
	}
}

func TestRunWithVerbosityEnvVar(t *testing.T) {
	env := mock.NewEnvironment()
	env.EnvLookup = func(key string) (string, bool) {
		if key == "DCOS_VERBOSITY" {
			return "2", true
		}
		return "", false
	}
	ctx := mock.NewContext(env)
	require.NoError(t, run(ctx, []string{"dcos"}))

	require.Equal(t, logrus.DebugLevel, ctx.Logger().Level)
}
