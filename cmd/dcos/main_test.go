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
