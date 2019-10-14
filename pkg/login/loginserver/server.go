package loginserver

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strings"

	"github.com/rs/cors"
)

// LoginServer can be used to automatically intercept login tokens.
type LoginServer struct {
	listener     net.Listener
	srv          *http.Server
	csrfToken    string
	startFlowURL string
	tokenCh      chan string
	errCh        chan error
}

// LoginData represents a login token and CSRF token pair.
type LoginData struct {
	Token     string `json:"token"`
	CSRFToken string `json:"csrf"`
}

// New creates a new login server.
func New(startFlowURL string) (*LoginServer, error) {
	ls := &LoginServer{
		tokenCh: make(chan string, 1),
		errCh:   make(chan error, 1),
	}

	// Parse start flow URL.
	u, err := url.Parse(startFlowURL)
	if err != nil {
		return nil, err
	}

	// Generate CSRF token.
	csrfTokenBytes := make([]byte, 32)
	_, err = rand.Read(csrfTokenBytes)
	if err != nil {
		return nil, err
	}
	ls.csrfToken = base64.StdEncoding.EncodeToString(csrfTokenBytes)

	// Create a listener to be used by the HTTP server.
	ls.listener, err = net.Listen("tcp", "localhost:0")
	if err != nil {
		return nil, err
	}

	// Create the new start flow URL.
	q := u.Query()
	q.Set("dcos_cli_flow", "v1")
	q.Set("dcos_cli_csrf_token", ls.csrfToken)

	// The auth0 page will validate the redirect URI and only continue the flow if it refers to localhost.
	// As such, we don't want to have 127.0.0.1 or [::1] as host, we enforce localhost.
	addr := strings.Split(ls.listener.Addr().String(), ":")
	q.Set("redirect_uri", fmt.Sprintf("http://localhost:%s", addr[len(addr)-1]))
	u.RawQuery = q.Encode()
	ls.startFlowURL = u.String()

	c := cors.New(cors.Options{
		AllowedOrigins: []string{"https://dcos.auth0.com"},
	})

	ls.srv = &http.Server{Handler: c.Handler(http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		var loginData LoginData

		err := json.NewDecoder(req.Body).Decode(&loginData)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if loginData.CSRFToken != ls.csrfToken {
			http.Error(w, "Invalid CSRF token.", http.StatusUnauthorized)
			return
		}
		ls.tokenCh <- loginData.Token
	}))}

	return ls, nil
}

// Start starts the login server.
func (ls *LoginServer) Start() error {
	return ls.srv.Serve(ls.listener)
}

// Close closes the login server.
func (ls *LoginServer) Close() error {
	return ls.srv.Close()
}

// StartFlowURL returns the start flow URL for the login server based flow.
func (ls *LoginServer) StartFlowURL() string {
	return ls.startFlowURL
}

// Token returns a channel from which the login token can be retrieved.
func (ls *LoginServer) Token() <-chan string {
	return ls.tokenCh
}
