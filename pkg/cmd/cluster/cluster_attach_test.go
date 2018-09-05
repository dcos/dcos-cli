package cluster

import (
	"bytes"
	"path/filepath"
	"testing"

	"github.com/dcos/dcos-cli/pkg/mock"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestClusterAttach(t *testing.T) {
	var out bytes.Buffer
	env := mock.NewEnvironment()
	env.Fs = afero.NewCopyOnWriteFs(
		afero.NewReadOnlyFs(afero.NewOsFs()),
		afero.NewMemMapFs(),
	)
	env.EnvLookup = func(key string) (string, bool) {
		if key == "DCOS_DIR" {
			return filepath.Join("testdata", "cluster_attach", ".dcos"), true
		}
		return "", false
	}
	env.Out = &out

	ctx := mock.NewContext(env)

	clusterID := "79893270-f9f1-4293-9225-e6e3900043a9"
	cmd := newCmdClusterAttach(ctx)
	cmd.SetArgs([]string{clusterID})

	require.NoError(t, cmd.Execute())

	cluster, err := ctx.Cluster()
	require.NoError(t, err)
	require.Equal(t, clusterID, cluster.ID())
}
