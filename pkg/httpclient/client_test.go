package httpclient

import (
	"crypto/tls"
	"crypto/x509"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

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

	client := New(ts.URL)

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

	client := New(ts.URL)

	resp, err := client.Post("/path", "application/json", strings.NewReader(`{"cluster":"DC/OS"}`))
	require.NoError(t, err)

	respBody, err := ioutil.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, "ok", string(respBody))
}

func TestNewRequest(t *testing.T) {
	client := New("https://dcos.io", func(client *Client) {
		client.acsToken = "acsToken"
	})

	req, err := client.NewRequest("GET", "/path", nil)
	require.NoError(t, err)
	require.Equal(t, req.URL.String(), "https://dcos.io/path")
	require.Equal(t, "token=acsToken", req.Header.Get("Authorization"))
}

func TestTimeout(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		timeout, err := time.ParseDuration(r.URL.Query().Get("timeout"))
		assert.NoError(t, err)
		time.Sleep(timeout)
	}))
	defer ts.Close()

	client := New(ts.URL, func(client *Client) {
		client.baseClient.Timeout = 50 * time.Millisecond
	})

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
		tls   *tls.Config
		valid bool
	}{
		// Using an empty TLS config should fail because the CA is not specified.
		{&tls.Config{}, false},

		// Using a TLS config with the actual CA should work.
		{&tls.Config{RootCAs: certPool}, true},

		// Using a TLS config with InsecureSkipVerify set to true should work.
		{&tls.Config{InsecureSkipVerify: true}, true},
	}

	for _, exp := range tlsConfigs {
		client := New(ts.URL, func(client *Client) {
			client.baseClient.Transport = &http.Transport{
				TLSClientConfig: exp.tls,
			}
		})

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
