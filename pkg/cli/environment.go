package cli

import (
	"io"
	"os"

	"github.com/spf13/afero"
)

// Environment variables for the DC/OS CLI.
const (
	// EnvStrictDeprecations indicates that the CLI should follow a strict deprecation policy.
	// If this var is exported, the CLI will fail on obsolete features. If a feature is deprecated
	// in favor of something else, the CLI will instead rely on the new approach. When this env var
	// is not exported, the CLI displays warnings when encountering deprecated features.
	EnvStrictDeprecations = "DCOS_CLI_STRICT_DEPRECATIONS"

	// EnvDCOSDir can be used to specify a custom directory for the DC/OS CLI data, which defaults to "~/.dcos".
	EnvDCOSDir = "DCOS_DIR"
)

// Environment represents the CLI environment. It contains writers for stdout/stderr,
// functions for environment variables or user lookup, as well as a filesystem abstraction.
type Environment struct {

	// Args are the command-line arguments, starting by the program name.
	Args []string

	// Input is the reader for CLI input.
	Input io.Reader

	// Out is the writer for CLI output.
	Out io.Writer

	// ErrOut is the writer for CLI errors, logs, and informational messages.
	ErrOut io.Writer

	// EnvLookup lookups environment variables.
	EnvLookup func(key string) (string, bool)

	// Fs is an abstraction for the filesystem.
	Fs afero.Fs
}

// NewOsEnvironment returns an environment backed by the os package.
func NewOsEnvironment() *Environment {
	return &Environment{
		Args:      os.Args,
		Input:     os.Stdin,
		Out:       os.Stdout,
		ErrOut:    os.Stderr,
		EnvLookup: os.LookupEnv,
		Fs:        afero.NewOsFs(),
	}
}
