package httpclient

import (
	"crypto/x509"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestGet(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "GET", r.Method)
		assert.Equal(t, "/path", r.URL.Path)
		w.Write([]byte("ok"))
	}))
	defer ts.Close()

	conf := config.New()
	conf.SetURL(ts.URL)

	client := New(conf)

	resp, err := client.Get("/path")
	require.NoError(t, err)

	respBody, err := ioutil.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, "ok", string(respBody))
}

func TestPost(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "POST", r.Method)
		assert.Equal(t, "/path", r.URL.Path)
		assert.Equal(t, "application/json", r.Header.Get("Content-Type"))

		body, err := ioutil.ReadAll(r.Body)
		assert.NoError(t, err)

		assert.Equal(t, `{"cluster":"DC/OS"}`, string(body))
		w.Write([]byte("ok"))
	}))
	defer ts.Close()

	conf := config.New()
	conf.SetURL(ts.URL)

	client := New(conf)

	resp, err := client.Post("/path", "application/json", strings.NewReader(`{"cluster":"DC/OS"}`))
	require.NoError(t, err)

	respBody, err := ioutil.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, "ok", string(respBody))
}

func TestNewRequest(t *testing.T) {
	conf := config.New()
	conf.SetACSToken("acsToken")
	conf.SetURL("https://dcos.io")

	client := New(conf)

	req, err := client.NewRequest("GET", "/path", nil)
	require.NoError(t, err)
	require.Equal(t, req.URL.String(), conf.URL()+"/path")
	require.Equal(t, "token="+conf.ACSToken(), req.Header.Get("Authorization"))
}

func TestTimeout(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		timeout, err := time.ParseDuration(r.URL.Query().Get("timeout"))
		assert.NoError(t, err)
		time.Sleep(timeout)
	}))
	defer ts.Close()

	conf := config.New()
	conf.SetURL(ts.URL)
	conf.SetTimeout(50 * time.Millisecond)

	client := New(conf)

	// The handler will sleep for 100ms with a client timeout of 50ms, the call should fail.
	req, err := client.NewRequest("GET", "/", nil)
	req.URL.RawQuery = "timeout=100ms"
	require.NoError(t, err)
	_, err = client.Do(req)
	require.Error(t, err)

	// The handler will sleep for 10ms with a client timeout of 50ms, the call should succeed.
	req, err = client.NewRequest("GET", "/", nil)
	req.URL.RawQuery = "timeout=10ms"
	require.NoError(t, err)
	_, err = client.Do(req)
	require.NoError(t, err)
}

func TestTLS(t *testing.T) {
	ts := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("ok"))
	}))
	defer ts.Close()

	certPool := x509.NewCertPool()
	certPool.AddCert(ts.Certificate())

	tlsConfigs := []struct {
		tls   config.TLS
		valid bool
	}{
		// Using an empty TLS config should fail because the CA is not specified.
		{config.TLS{}, false},

		// Using a TLS config with the actual CA should work.
		{config.TLS{RootCAs: certPool}, true},

		// Using a TLS config with Insecure set to true should work.
		{config.TLS{Insecure: true}, true},
	}

	conf := config.New()
	conf.SetURL(ts.URL)

	for _, exp := range tlsConfigs {
		conf.SetTLS(exp.tls)

		client := New(conf)
		resp, err := client.Get("/")
		if exp.valid {
			require.NoError(t, err)
			respBody, err := ioutil.ReadAll(resp.Body)
			require.NoError(t, err)
			require.Equal(t, "ok", string(respBody))
		} else {
			require.Error(t, err)
			require.Nil(t, resp)
		}
	}
}
