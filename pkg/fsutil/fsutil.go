package fsutil

import (
	"fmt"
	"io/ioutil"
	"runtime"

	"github.com/spf13/afero"
)

// ReadSecureFile ensures a file has 0400 or 0600 permissions before reading it.
// Permissions check is skipped on Windows as it uses a different mechanism than UNIX.
func ReadSecureFile(fs afero.Fs, filename string) ([]byte, error) {
	f, err := fs.Open(filename)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	if runtime.GOOS != "windows" {
		fi, err := f.Stat()
		if err != nil {
			return nil, err
		}
		perm := fi.Mode().Perm()
		if perm&0177 != 0 {
			return nil, fmt.Errorf(
				"permissions %#o for '%s' are too open, expected 0400 or 0600", perm, filename)
		}
	}
	return ioutil.ReadAll(f)
}
