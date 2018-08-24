package cosmos

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/dcos/dcos-cli/pkg/httpclient"
)

func TestPackageDescribe(t *testing.T) {
	mux := http.NewServeMux()

	mux.HandleFunc("/package/describe", func(w http.ResponseWriter, req *http.Request) {
		assert.Equal(t, "POST", req.Method)
		assert.Equal(
			t,
			"application/vnd.dcos.package.describe-response+json;charset=utf-8;version=v3",
			req.Header.Get("Accept"),
		)
		assert.Equal(
			t,
			"application/vnd.dcos.package.describe-request+json;charset=utf-8;version=v1",
			req.Header.Get("Content-Type"),
		)
		payload := map[string]string{}
		err := json.NewDecoder(req.Body).Decode(&payload)
		assert.NoError(t, err)
		assert.Equal(t, "dcos-test-cli", payload["packageName"])

		var pkgInfo PackageInfo

		pkgInfo.Package.Resource.CLI.Plugins = map[string]map[string]*Plugin{
			"linux": map[string]*Plugin{
				"x86-64": &Plugin{
					Kind: "zip",
					URL:  "https://linux.example.com/dcos-test-cli.zip",
				},
			},
			"darwin": map[string]*Plugin{
				"x86-64": &Plugin{
					Kind: "zip",
					URL:  "http://darwin.example.com/dcos-test-cli.zip",
				},
			},
			// Test case against scheme mismatch between `core.dcos_url` and Cosmos resources.
			"windows": map[string]*Plugin{
				"x86-64": &Plugin{
					Kind: "zip",
					URL:  "https://" + req.Host + "/dcos-test-cli.zip",
				},
			},
		}

		err = json.NewEncoder(w).Encode(&pkgInfo)
		assert.NoError(t, err)
	})

	ts := httptest.NewServer(mux)
	defer ts.Close()

	client := NewClient(httpclient.New(ts.URL))

	pkgInfo, err := client.DescribePackage("dcos-test-cli")
	require.NoError(t, err)

	linuxPlugin, ok := pkgInfo.Package.Resource.CLI.Plugins["linux"]["x86-64"]
	require.True(t, ok)
	require.Equal(t, "zip", linuxPlugin.Kind)
	require.Equal(t, "https://linux.example.com/dcos-test-cli.zip", linuxPlugin.URL)

	darwinPlugin, ok := pkgInfo.Package.Resource.CLI.Plugins["darwin"]["x86-64"]
	require.True(t, ok)
	require.Equal(t, "zip", darwinPlugin.Kind)
	require.Equal(t, "http://darwin.example.com/dcos-test-cli.zip", darwinPlugin.URL)

	windowsPlugin, ok := pkgInfo.Package.Resource.CLI.Plugins["windows"]["x86-64"]
	require.True(t, ok)
	require.Equal(t, "zip", windowsPlugin.Kind)
	require.Equal(t, ts.URL+"/dcos-test-cli.zip", windowsPlugin.URL)
}

func TestPermissionError(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/package/describe", func(w http.ResponseWriter, req *http.Request) {
		w.WriteHeader(http.StatusForbidden)
	})
	ts := httptest.NewServer(mux)
	defer ts.Close()
	client := NewClient(httpclient.New(ts.URL))
	_, err := client.DescribePackage("dcos-test-cli")
	require.Error(t, err)
	assert.Equal(t, ErrForbidden, err)
}

func TestOtherError(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/package/describe", func(w http.ResponseWriter, req *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})
	ts := httptest.NewServer(mux)
	defer ts.Close()
	client := NewClient(httpclient.New(ts.URL))
	_, err := client.DescribePackage("dcos-test-cli")
	require.Error(t, err)
	assert.NotEqual(t, ErrForbidden, err)
}
