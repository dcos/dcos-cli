package loginserver

import (
	"bytes"
	"encoding/json"
	"net/url"
	"testing"

	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestServe(t *testing.T) {
	loginServer, err := New("https://dcos.example.com")
	require.NoError(t, err)

	startFlowURL, err := url.Parse(loginServer.StartFlowURL())
	require.NoError(t, err)

	require.Equal(t, "v1", startFlowURL.Query().Get("dcos_cli_flow"))

	go func() {
		err := loginServer.Start()
		assert.NoError(t, err)
	}()

	loginData := &LoginData{
		Token:     "abc",
		CSRFToken: startFlowURL.Query().Get("dcos_cli_csrf_token"),
	}

	var buf bytes.Buffer
	err = json.NewEncoder(&buf).Encode(loginData)
	require.NoError(t, err)

	resp, err := httpclient.New("").Post(startFlowURL.Query().Get("redirect_uri"), "application/json", &buf)
	require.NoError(t, err)
	require.Equal(t, 200, resp.StatusCode)

	require.Equal(t, loginData.Token, <-loginServer.Token())
}

func TestServeMissingCSRFToken(t *testing.T) {
	loginServer, err := New("https://dcos.example.com")
	require.NoError(t, err)

	startFlowURL, err := url.Parse(loginServer.StartFlowURL())
	require.NoError(t, err)

	go func() {
		err := loginServer.Start()
		assert.NoError(t, err)
	}()

	loginData := &LoginData{Token: "abc"}

	var buf bytes.Buffer
	err = json.NewEncoder(&buf).Encode(loginData)
	require.NoError(t, err)

	resp, err := httpclient.New("").Post(startFlowURL.Query().Get("redirect_uri"), "application/json", &buf)
	require.NoError(t, err)
	require.Equal(t, 401, resp.StatusCode)
}
