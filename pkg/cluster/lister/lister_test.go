package lister

import (
	"bytes"
	"net/http/httptest"
	"path/filepath"
	"testing"

	"github.com/dcos/dcos-cli/pkg/cluster/linker"
	"github.com/sirupsen/logrus/hooks/test"

	"github.com/stretchr/testify/require"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/mock"
)

func TestEmptyList(t *testing.T) {
	env := mock.NewEnvironment()

	logger, _ := test.NewNullLogger()
	lister := New(config.NewManager(config.ManagerOpts{
		Fs:        env.Fs,
		EnvLookup: env.EnvLookup,
	}), logger)

	items := lister.List(false)
	require.Len(t, items, 0)

	items = lister.List(true)
	require.Len(t, items, 0)
}

func TestList(t *testing.T) {
	env := mock.NewEnvironment()

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

	ts := mock.NewTestServer(mock.Cluster{Version: "1.12"})
	defer ts.Close()
	currentCluster := newCluster("1234-56789-01234", "current-cluster", ts.URL, true)

	ts2 := mock.NewTestServer(mock.Cluster{Version: "1.18"})
	defer ts2.Close()
	otherCluster := newCluster("2234-56789-01234", "other-cluster", ts2.URL, false)

	ts3 := httptest.NewServer(nil)
	defer ts.Close()
	downCluster := newCluster("3234-56789-01234", "invalid-cluster", ts3.URL, false)

	logger, _ := test.NewNullLogger()
	lister := New(config.NewManager(config.ManagerOpts{
		Fs:        env.Fs,
		EnvLookup: env.EnvLookup,
	}), logger)

	items := lister.List(false)
	require.Len(t, items, 3)

	require.Equal(t, currentCluster.URL(), items[0].URL)
	require.Equal(t, "AVAILABLE", items[0].Status)
	require.Equal(t, "1234-56789-01234", items[0].ID)
	require.Equal(t, "current-cluster", items[0].Name)
	require.Equal(t, "1.12", items[0].Version)

	require.Equal(t, downCluster.URL(), items[1].URL)
	require.Equal(t, "UNAVAILABLE", items[1].Status)
	require.Equal(t, "3234-56789-01234", items[1].ID)
	require.Equal(t, "invalid-cluster", items[1].Name)
	require.Equal(t, "UNKNOWN", items[1].Version)

	require.Equal(t, otherCluster.URL(), items[2].URL)
	require.Equal(t, "AVAILABLE", items[2].Status)
	require.Equal(t, "2234-56789-01234", items[2].ID)
	require.Equal(t, "other-cluster", items[2].Name)
	require.Equal(t, "1.18", items[2].Version)
}

func TestListIgnoresLegacyConfig(t *testing.T) {
	var out bytes.Buffer
	env := mock.NewEnvironment()
	env.Out = &out

	conf := config.New(config.Opts{Fs: env.Fs})
	conf.SetPath("dcos.toml")

	config.NewManager(config.ManagerOpts{
		Fs:        env.Fs,
		EnvLookup: env.EnvLookup,
	})

	logger, _ := test.NewNullLogger()
	lister := New(config.NewManager(config.ManagerOpts{
		Fs:        env.Fs,
		EnvLookup: env.EnvLookup,
	}), logger)
	require.Len(t, lister.List(true), 0)
	require.Len(t, lister.List(false), 0)
}

func TestListLegacyConfigWithLink(t *testing.T) {
	var out bytes.Buffer
	env := mock.NewEnvironment()
	env.Out = &out

	linkTS := mock.NewTestServer(mock.Cluster{Version: "1.15"})
	defer linkTS.Close()

	link := &linker.Link{
		ID:   "22c85511-4f0c-42e7-80d2-c697796e47f1",
		Name: "Zelda",
		URL:  linkTS.URL,
		LoginProvider: linker.LoginProvider{
			ID:   "dcos-users",
			Type: "dcos-credential-post-receive-authtoken",
		},
	}

	ts := mock.NewTestServer(mock.Cluster{
		Links: []*linker.Link{link},
	})
	defer ts.Close()

	conf := config.New(config.Opts{Fs: env.Fs})
	conf.Set("core.dcos_url", ts.URL)
	conf.SetPath("dcos.toml")
	conf.Persist()

	logger, _ := test.NewNullLogger()
	lister := New(config.NewManager(config.ManagerOpts{
		Fs:        env.Fs,
		EnvLookup: env.EnvLookup,
	}), logger)

	require.Len(t, lister.List(true), 0)

	items := lister.List(false)
	require.Len(t, items, 1)
	require.Equal(t, "22c85511-4f0c-42e7-80d2-c697796e47f1", items[0].ID)
	require.Equal(t, "Zelda", items[0].Name)
	require.Equal(t, linkTS.URL, items[0].URL)
	require.Equal(t, "UNCONFIGURED", items[0].Status)
	require.Equal(t, "1.15", items[0].Version)
}
