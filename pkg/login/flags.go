package login

import (
	"bytes"
	"crypto/rsa"
	"fmt"
	"unicode"

	"github.com/dcos/dcos-cli/pkg/fsutil"
	jwt "github.com/dgrijalva/jwt-go"
	"github.com/spf13/afero"
	"github.com/spf13/pflag"
)

// Flags are command-line flags for a login flow.
type Flags struct {
	fs             afero.Fs
	envLookup      func(key string) (string, bool)
	providerID     string
	username       string
	password       string
	passwordEnv    string
	passwordFile   string
	privateKey     *rsa.PrivateKey
	privateKeyFile string
}

// NewFlags creates flags for a login flow.
func NewFlags(fs afero.Fs, envLookup func(key string) (string, bool)) *Flags {
	return &Flags{
		fs:        fs,
		envLookup: envLookup,
	}
}

// Register registers login flags.
func (f *Flags) Register(flags *pflag.FlagSet) {
	flags.StringVar(
		&f.providerID,
		"provider",
		"",
		"Specify the authentication provider to use for login.",
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
		&f.passwordEnv,
		"password-env",
		"",
		"Specify an environment variable name that contains the password.",
	)
	flags.StringVar(
		&f.passwordFile,
		"password-file",
		"",
		"Specify the path to a file that contains the password (insecure).",
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

	if f.passwordEnv != "" {
		if password, ok := f.envLookup(f.passwordEnv); ok {
			f.password = password
		} else {
			return fmt.Errorf("couldn't read password from '%s' env var", f.passwordEnv)
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
	return f.privateKey == nil
}
