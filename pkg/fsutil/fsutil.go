package fsutil

import (
	"archive/zip"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"path/filepath"
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

// Unzip extracts a ZIP archive into a given destination.
func Unzip(fs afero.Fs, src, dest string) error {
	f, err := fs.Open(src)
	if err != nil {
		return err
	}
	defer f.Close()

	fi, err := f.Stat()
	if err != nil {
		return err
	}

	r, err := zip.NewReader(f, fi.Size())
	if err != nil {
		return err
	}

	for _, f := range r.File {
		unzipFile(fs, f, dest)
	}
	return nil
}

// unzipFile extracts a zip.File to a given destination.
func unzipFile(fs afero.Fs, f *zip.File, dest string) error {
	rc, err := f.Open()
	if err != nil {
		return err
	}
	defer rc.Close()

	fpath := filepath.Join(dest, f.Name)

	if f.FileInfo().IsDir() {
		return fs.MkdirAll(fpath, f.FileInfo().Mode())
	}

	if err := fs.MkdirAll(filepath.Dir(fpath), 0755); err != nil {
		return err
	}

	outFile, err := fs.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
	if err != nil {
		return err
	}

	_, err = io.Copy(outFile, rc)
	outFile.Close()
	return err
}
