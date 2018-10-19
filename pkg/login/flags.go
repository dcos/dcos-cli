package login

import (
	"bytes"
	"crypto/rsa"
	"strings"
	"unicode"

	"github.com/dcos/dcos-cli/pkg/fsutil"
	jwt "github.com/dgrijalva/jwt-go"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/spf13/pflag"
)

// Flags are command-line flags for a login flow.
type Flags struct {
	fs             afero.Fs
	logger         *logrus.Logger
	envLookup      func(key string) (string, bool)
	providerID     string
	username       string
	password       string
	passwordFile   string
	privateKey     *rsa.PrivateKey
	privateKeyFile string
}

// NewFlags creates flags for a login flow.
func NewFlags(fs afero.Fs, envLookup func(key string) (string, bool), logger *logrus.Logger) *Flags {
	return &Flags{
		fs:        fs,
		envLookup: envLookup,
		logger:    logger,
	}
}

// Register registers login flags.
func (f *Flags) Register(flags *pflag.FlagSet) {
	flags.StringVar(
		&f.providerID,
		"provider",
		"",
		"Specify the login provider to use.",
	)
	flags.StringVar(
		&f.username,
		"username",
		"",
		"Specify the username for login.",
	)
	flags.StringVar(
		&f.password,
		"password",
		"",
		"Specify the password on the command line (insecure).",
	)
	flags.StringVar(
		&f.passwordFile,
		"password-file",
		"",
		"Specify the path to a file that contains the password.",
	)
	flags.StringVar(
		&f.privateKeyFile,
		"private-key",
		"",
		"Specify the path to a file that contains the service account private key.",
	)
}

// Resolve resolves credentials from --password-env, --password-file and --private-key flags.
func (f *Flags) Resolve() error {
	if f.passwordFile != "" {
		rawPassword, err := fsutil.ReadSecureFile(f.fs, f.passwordFile)
		if err != nil {
			return err
		}
		rawPassword = bytes.TrimRightFunc(rawPassword, unicode.IsSpace)
		f.password = string(rawPassword)
	}

	if f.username == "" {
		if username, ok := f.envLookup("DCOS_USERNAME"); ok {
			f.username = username
			f.logger.Info("Read username from environment.")
		}
	}

	if f.password == "" {
		if password, ok := f.envLookup("DCOS_PASSWORD"); ok {
			f.password = password
			f.logger.Info("Read password from environment.")
		}
	}

	if f.privateKeyFile != "" {
		privateKeyPEM, err := fsutil.ReadSecureFile(f.fs, f.privateKeyFile)
		if err != nil {
			return err
		}
		f.privateKey, err = jwt.ParseRSAPrivateKeyFromPEM(privateKeyPEM)
		if err != nil {
			return err
		}
	}
	return nil
}

// SetProviderID sets the provider ID.
func (f *Flags) SetProviderID(providerID string) {
	f.providerID = providerID
}

// Supports indicates whether or not a provider is supported based on the specified flags.
func (f *Flags) Supports(provider *Provider) bool {
	if provider.Type == DCOSUIDServiceKey {
		// The private key can't be passed interactively,
		// if the flag is empty this provider is not supported.
		return f.privateKey != nil
	}
	if strings.HasPrefix(provider.ClientMethod, "browser-") {
		// A browser based login flow doesn't support passing a username, password, or private key
		// from the command-line. It must be skipped implicitly in such cases.
		return f.username == "" && f.password == "" && f.privateKey == nil
	}
	return f.privateKey == nil
}
