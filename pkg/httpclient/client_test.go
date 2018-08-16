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

	"github.com/sirupsen/logrus"
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
	client := New("https://dcos.io", ACSToken("acsToken"), Timeout(60*time.Second))

	req, err := client.NewRequest("GET", "/path", nil)
	require.NoError(t, err)
	require.Equal(t, req.URL.String(), "https://dcos.io/path")
	require.Equal(t, "token=acsToken", req.Header.Get("Authorization"))
	_, ok := req.Context().Deadline()
	require.True(t, ok)
}

func TestNewRequestWithoutTimeout(t *testing.T) {
	client := New("https://dcos.io", Timeout(60*time.Second))

	req, err := client.NewRequest("GET", "/path", nil, Timeout(0))
	require.NoError(t, err)
	_, ok := req.Context().Deadline()
	require.False(t, ok)
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
		client := New(ts.URL, TLS(exp.tls))

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

func TestLogger(t *testing.T) {
	logger := &logrus.Logger{Out: ioutil.Discard}
	client := New("", Logger(logger))
	require.Equal(t, client.opts.Logger, logger)
}

func TestFailOnError(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(404)
	}))
	defer ts.Close()

	client := New(ts.URL)

	resp, err := client.Get("/")
	require.NoError(t, err)
	require.Equal(t, resp.StatusCode, 404)

	_, err = client.Get("/", FailOnErrStatus(true))
	require.Error(t, err)
}

func TestDefaultUserAgent(t *testing.T) {
	client := New("https://example.com")

	// Custom User-Agent.
	req, err := client.NewRequest("GET", "/", nil, Header("User-Agent", "Mario/Nintendo64"))
	require.NoError(t, err)
	require.Equal(t, "Mario/Nintendo64", req.Header.Get("User-Agent"))

	// Explicitly empty User-Agent.
	req, err = client.NewRequest("GET", "/", nil, Header("User-Agent", ""))
	require.NoError(t, err)
	require.Equal(t, "", req.Header.Get("User-Agent"))

	// No User-Agent.
	req, err = client.NewRequest("GET", "/", nil)
	require.NoError(t, err)
	require.Equal(t, defaultUserAgent, req.Header.Get("User-Agent"))
}

func TestIsText(t *testing.T) {
	client := New("")

	fixtures := []struct {
		contentType string
		isText      bool
	}{
		{"text/plain", true},
		{"text/html", true},
		{"application/json", true},
		{"application/vnd.dcos.package.describe-response+json;charset=utf-8;version=v3", true},
		{"application/octet-stream", false},
	}
	for _, fixture := range fixtures {
		require.Equal(t, fixture.isText, client.isText(fixture.contentType))
	}
}
