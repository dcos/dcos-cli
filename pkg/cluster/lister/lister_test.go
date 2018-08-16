package lister

import (
	"bytes"
	"net/http/httptest"
	"path/filepath"
	"testing"

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

	items := lister.List()
	require.NotNil(t, items)
	require.Len(t, items, 0)

	items = lister.List(AttachedOnly())
	require.NotNil(t, items)
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

	items := lister.List()
	require.Len(t, items, 3)

	require.Equal(t, currentCluster.URL(), items[0].URL)
	require.Equal(t, StatusAvailable, items[0].Status)
	require.Equal(t, "1234-56789-01234", items[0].ID)
	require.Equal(t, "current-cluster", items[0].Name)
	require.Equal(t, "1.12", items[0].Version)

	require.Equal(t, downCluster.URL(), items[1].URL)
	require.Equal(t, StatusUnavailable, items[1].Status)
	require.Equal(t, "3234-56789-01234", items[1].ID)
	require.Equal(t, "invalid-cluster", items[1].Name)
	require.Equal(t, "UNKNOWN", items[1].Version)

	require.Equal(t, otherCluster.URL(), items[2].URL)
	require.Equal(t, StatusAvailable, items[2].Status)
	require.Equal(t, "2234-56789-01234", items[2].ID)
	require.Equal(t, "other-cluster", items[2].Name)
	require.Equal(t, "1.18", items[2].Version)

	// Test the Status filter.
	items = lister.List(Status(StatusUnavailable))
	require.Len(t, items, 1)

	require.Equal(t, downCluster.URL(), items[0].URL)
	require.Equal(t, StatusUnavailable, items[0].Status)
	require.Equal(t, "3234-56789-01234", items[0].ID)
	require.Equal(t, "invalid-cluster", items[0].Name)
	require.Equal(t, "UNKNOWN", items[0].Version)
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
	require.Len(t, lister.List(AttachedOnly()), 0)
	require.Len(t, lister.List(), 0)
}
