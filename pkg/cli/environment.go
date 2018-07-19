package cli

import (
	"io"
	"os/user"

	"github.com/spf13/afero"
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

	// UserLookup returns the current system user.
	UserLookup func() (*user.User, error)

	// Fs is an abstraction for the filesystem.
	Fs afero.Fs
}
