package httpclient

import (
	"crypto/tls"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNew(t *testing.T) {
	acsToken := "acsToken"
	url := "https://dcos.io"

	conf := config.New()
	conf.SetURL("https://dcos.io")
	conf.SetACSToken(acsToken)

	client := New(conf)

	tlsConfig := &tls.Config{
		InsecureSkipVerify: conf.TLS().Insecure,
		RootCAs:            conf.TLS().RootCAs,
	}
	transport := &http.Transport{
		TLSClientConfig: tlsConfig,
	}
	backendClient := &http.Client{
		Transport: transport,
		Timeout:   conf.Timeout(),
	}
	expectedClient := &Client{
		acsToken: acsToken,
		baseURL:  url,
		client:   backendClient,
	}

	require.Equal(t, expectedClient, client)
}

func TestGet(t *testing.T) {
	body := `{"cluster":"DC/OS"}`
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "GET", r.Method)
		assert.Equal(t, "/get", r.URL.EscapedPath())

		w.Write([]byte(body))
	}))
	defer ts.Close()

	conf := config.New()
	conf.SetURL(ts.URL)

	client := New(conf)

	resp, err := client.Get("/get")
	require.NoError(t, err)

	respBody, err := ioutil.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, body, string(respBody))
}

func TestPost(t *testing.T) {
	body := `{"cluster":"DC/OS"}`

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "POST", r.Method)
		assert.Equal(t, "/post", r.URL.EscapedPath())

		body, err := ioutil.ReadAll(r.Body)
		assert.NoError(t, err)

		assert.Equal(t, string(body), `{"cluster":"DC/OS"}`)
	}))
	defer ts.Close()

	conf := config.New()
	conf.SetURL(ts.URL)

	client := New(conf)

	resp, err := client.Post("/post", "application/json", strings.NewReader(body))
	require.NoError(t, err)
	require.Equal(t, resp.StatusCode, http.StatusOK)
}

func TestACSToken(t *testing.T) {
	body := `{"cluster":"DC/OS"}`
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "GET", r.Method)
		assert.Equal(t, "/get", r.URL.EscapedPath())
		assert.Equal(t, "token=secret", r.Header.Get("Authorization"))

		w.Write([]byte(body))
	}))
	defer ts.Close()

	conf := config.New()
	conf.SetURL(ts.URL)
	conf.SetACSToken("secret")

	client := New(conf)

	resp, err := client.Get("/get")
	require.NoError(t, err)

	respBody, err := ioutil.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, body, string(respBody))
}

func TestNewRequest(t *testing.T) {
	acsToken := "acsToken"
	url := "https://dcos.io/"
	baseURL := "https://dcos.io"

	conf := config.New()
	conf.SetACSToken(acsToken)
	conf.SetURL(url)

	client := New(conf)

	req, err := client.NewRequest("GET", "/get", nil)
	require.NoError(t, err)
	require.Equal(t, req.URL.Scheme+"://"+req.URL.Host, baseURL)
}
