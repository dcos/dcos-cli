package cluster

import (
	"bytes"
	"net/http/httptest"
	"path/filepath"
	"testing"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/mock"
	"github.com/stretchr/testify/require"
)

func TestClusterListTable(t *testing.T) {
	var out bytes.Buffer
	env := mock.NewEnvironment()
	env.Out = &out

	newCluster := func(id, name, url string, attached bool) *cli.Cluster {
		conf := config.New(config.Opts{Fs: env.Fs})
		conf.Set("core.dcos_url", url)
		conf.Set("cluster.name", name)
		conf.SetPath(filepath.Join("clusters", id, "dcos.toml"))
		if attached {
			env.Fs.Create(filepath.Join("clusters", id, "attached"))
			conf.Persist()
		}
		return cli.NewCluster(conf)
	}

	ts := mock.NewTestServer(mock.Cluster{Version: "1.12"})
	defer ts.Close()
	currentCluster := newCluster("1234-56789-01234", "current-cluster", ts.URL, true)

	ts2 := mock.NewTestServer(mock.Cluster{Version: "1.18"})
	defer ts2.Close()
	otherCluster := newCluster("2234-56789-01234", "other-cluster", ts2.URL, false)

	ts3 := httptest.NewServer(nil)
	defer ts.Close()
	downCluster := newCluster("3234-56789-01234", "invalid-cluster", ts3.URL, false)

	ctx := mock.NewContext(env)
	ctx.SetClusters([]*cli.Cluster{currentCluster, otherCluster, downCluster})

	err := newCmdClusterList(ctx).Execute()
	require.NoError(t, err)

	var exp bytes.Buffer
	table := cli.NewTable(&exp, []string{"", "NAME", "ID", "STATUS", "VERSION", "URL"})
	table.Append([]string{"*", "current-cluster", "1234-56789-01234", "AVAILABLE", "1.12", ts.URL})
	table.Append([]string{"", "invalid-cluster", "3234-56789-01234", "UNAVAILABLE", "UNKNOWN", ts3.URL})
	table.Append([]string{"", "other-cluster", "2234-56789-01234", "AVAILABLE", "1.18", ts2.URL})

	table.Render()
	require.Equal(t, exp.String(), out.String())
}
