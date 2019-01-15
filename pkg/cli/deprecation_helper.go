package cli

import (
	"errors"
	"fmt"
	"io"
	"os"
)

// DeprecationHelperOpts are functional options for a DeprecationHelper.
type DeprecationHelperOpts struct {
	// Output is where deprecation messages should be printed to.
	Output io.Writer

	// EnvLookup is the function looking-up environment variables.
	EnvLookup func(key string) (string, bool)
}

// NewDeprecationHelper returns a new deprecation helper function.
func NewDeprecationHelper(opts DeprecationHelperOpts) func(msg string) error {
	if opts.Output == nil {
		opts.Output = os.Stderr
	}
	if opts.EnvLookup == nil {
		opts.EnvLookup = os.LookupEnv
	}
	return func(msg string) error {
		fmt.Fprintln(opts.Output, msg)
		if _, ok := opts.EnvLookup("DCOS_CLI_FAIL_ON_DEPRECATION"); ok {
			return errors.New("usage of deprecated feature (DCOS_CLI_FAIL_ON_DEPRECATION=1)")
		}
		return nil
	}
}
