//+build !corecli

package corecli

import "errors"

// Asset returns an error message when the CLI hasn't been built with the corecli tag.
func Asset(name string) ([]byte, error) {
	return nil, errors.New("no core CLI is bundled in the binary")
}
