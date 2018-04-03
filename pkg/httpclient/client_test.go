package httpclient

import (
	"context"
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

func TestCancelRequest(t *testing.T) {
	done := make(chan struct{})
	stuckHandler := make(chan struct{})
	canceler := make(chan context.CancelFunc, 1)

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		cancel := <-canceler
		cancel()
		<-stuckHandler
	}))
	defer ts.Close()
	defer close(stuckHandler)

	client := New(ts.URL)

	req, err := client.NewRequest("GET", "/", nil)
	require.NoError(t, err)

	// Create a cancelable request and send the cancel function to a channel.
	// The HTTP handler will then invoke it, this simulates a test where the
	// request timeout is reached while the server is still processing it.
	newCtx, cancel := context.WithCancel(req.Context())
	req = req.WithContext(newCtx)
	canceler <- cancel

	go func() {
		resp, err := client.Do(req)
		require.Error(t, err)
		require.Nil(t, resp)
		close(done)
	}()

	select {
	case <-time.After(5 * time.Second):
		require.Fail(t, "HTTP client didn't error-out within 5 seconds, it is most likely stuck forever.")
	case <-done:
	}
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
