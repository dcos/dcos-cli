package setup

import (
	"net/http"
	"net/http/httptest"
	"testing"

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
