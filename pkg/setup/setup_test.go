package setup

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/sirupsen/logrus"
	logrustest "github.com/sirupsen/logrus/hooks/test"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestCanonicalURLHostCase(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "HEAD", r.Method)
		assert.Equal(t, "/", r.URL.Path)

		http.Redirect(w, r, "https://www.ExAmPlE.org", 301)
	}))
	defer ts.Close()

	canonicalURL, err := detectCanonicalClusterURL(ts.URL, nil)
	require.NoError(t, err)
	require.Equal(t, "https://www.example.org", canonicalURL)
}

func TestDefaultPluginsRequirements(t *testing.T) {
	logger, hook := logrustest.NewNullLogger()
	flow := New(Opts{
		Logger: logger,
	})

	require.Error(t, flow.checkDefaultPluginsRequirements("1.7.5"))
	require.Error(t, flow.checkDefaultPluginsRequirements("1.8.4"))
	require.Error(t, flow.checkDefaultPluginsRequirements("1.9.3"))

	require.NoError(t, flow.checkDefaultPluginsRequirements("1.10.0"))
	require.NoError(t, flow.checkDefaultPluginsRequirements("1.11.4"))
	require.NoError(t, flow.checkDefaultPluginsRequirements("1.12.2"))
	require.NoError(t, flow.checkDefaultPluginsRequirements("1.13.1"))
	require.NoError(t, flow.checkDefaultPluginsRequirements("2.0.0-alpha"))
	require.NoError(t, flow.checkDefaultPluginsRequirements("2.0.74"))

	require.NoError(t, flow.checkDefaultPluginsRequirements("V3"))
	entry := hook.LastEntry()
	require.Equal(t, logrus.WarnLevel, entry.Level)
	require.Equal(t, `Couldn't parse DC/OS version "V3".`, entry.Message)
}
