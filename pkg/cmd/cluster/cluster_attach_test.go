package cluster

import (
	"bytes"
	"path/filepath"
	"testing"

	"github.com/dcos/dcos-cli/pkg/cluster/linker"
	"github.com/dcos/dcos-cli/pkg/config"
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

func TestClusterAttachBothConfiguredAndLinked(t *testing.T) {
	env := mock.NewEnvironment()
	env.EnvLookup = func(key string) (string, bool) {
		if key == "DCOS_DIR" {
			return "", true
		}
		return "", false
	}

	newCluster := func(id, name, url string, attached bool) *config.Cluster {
		conf := config.New(config.Opts{Fs: env.Fs})
		conf.Set("core.dcos_url", url)
		conf.Set("cluster.name", name)
		conf.SetPath(filepath.Join("clusters", id, "dcos.toml"))
		if attached {
			_, err := env.Fs.Create(filepath.Join("clusters", id, "attached"))
			require.NoError(t, err)
		}
		require.NoError(t, conf.Persist())
		return config.NewCluster(conf)
	}

	linkedCluster := newCluster("2234-56789-01234", "linked-and-configured", "https://example.com", false)

	ts := mock.NewTestServer(mock.Cluster{
		Links: []*linker.Link{
			&linker.Link{
				ID:   linkedCluster.ID(),
				Name: linkedCluster.Name(),
				URL:  linkedCluster.URL(),
			},
		},
	})
	defer ts.Close()
	newCluster("1234-56789-01234", "current", ts.URL, true)

	clusterID := "2234-56789-01234"
	ctx := mock.NewContext(env)
	cmd := newCmdClusterAttach(ctx)
	cmd.SetArgs([]string{clusterID})

	require.NoError(t, cmd.Execute())

	cluster, err := ctx.Cluster()
	require.NoError(t, err)
	require.Equal(t, clusterID, cluster.ID())
}
