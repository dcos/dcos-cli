package setup

import (
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/spf13/pflag"
)

// Flags are command-line flags for a cluster setup.
type Flags struct {
	caBundle     []byte
	caBundlePath string
	name         string
	noCheck      bool
	insecure     bool
	loginFlags   *login.Flags
	fs           afero.Fs
	noTimeout    bool
}

// NewFlags creates flags for a cluster setup.
func NewFlags(fs afero.Fs, envLookup func(key string) (string, bool), logger *logrus.Logger) *Flags {
	return &Flags{
		fs:         fs,
		loginFlags: login.NewFlags(fs, envLookup, logger),
	}
}

// Register registers cluster setup flags.
func (f *Flags) Register(flags *pflag.FlagSet) {
	flags.BoolVar(
		&f.insecure,
		"insecure",
		false,
		"Allow requests to bypass TLS certificate verification (insecure)."+
			" It controls whether a client verifies the"+
			" server's certificate chain and host name."+
			" If flag is specified, TLS accepts any certificate"+
			" presented by the server and any host name in that certificate."+
			" In this mode, TLS is susceptible to man-in-the-middle attacks."+
			" This should be used only for testing.",
	)
	flags.BoolVar(
		&f.noCheck,
		"no-check",
		false,
		"Do not ask user for certificate confirmation (insecure). Applies to Enterprise DC/OS only.",
	)
	flags.StringVar(
		&f.caBundlePath,
		"ca-certs",
		"",
		"Specify the path to a file with trusted CAs to verify requests against. This also sets --no-check.",
	)
	flags.StringVar(
		&f.name,
		"name",
		"",
		"Specify a custom name for the cluster.",
	)
	flags.BoolVar(
		&f.noTimeout,
		"no-timeout",
		false,
		"Specify if HTTP timeout should be disabled. Useful for slow remote connections.",
	)
	f.loginFlags.Register(flags)
}

// Resolve resolves setup and login flags.
func (f *Flags) Resolve() error {
	if f.caBundlePath != "" {
		caBundle, err := afero.ReadFile(f.fs, f.caBundlePath)
		if err != nil {
			return err
		}
		f.caBundle = caBundle

		// Don't prompt for fingerprint confirmation when a CA is explicitly passed.
		f.noCheck = true
	}
	return f.loginFlags.Resolve()
}

// LoginFlags returns the login flags.
func (f *Flags) LoginFlags() *login.Flags {
	return f.loginFlags
}
