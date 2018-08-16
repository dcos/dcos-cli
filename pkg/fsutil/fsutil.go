package fsutil

import (
	"archive/zip"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"os"
	"path/filepath"
	"runtime"

	"github.com/spf13/afero"
)

// Copy copies a file into a given destination.
func Copy(fs afero.Fs, src, dest string, perm os.FileMode) error {
	srcFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	return CopyReader(fs, srcFile, dest, perm)
}

// CopyReader copies an io.Reader into a given destination.
func CopyReader(fs afero.Fs, r io.Reader, dest string, perm os.FileMode) error {
	destFile, err := fs.OpenFile(dest, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, perm)
	if err != nil {
		return err
	}
	defer destFile.Close()

	_, err = io.Copy(destFile, r)
	return err
}

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

// DetectMediaType detects a file's media type, as defined in
// https://www.iana.org/assignments/media-types/media-types.xhtml.
func DetectMediaType(fs afero.Fs, path string) (string, error) {
	f, err := fs.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()

	sniffBuf := make([]byte, 512)
	if _, err := io.ReadFull(f, sniffBuf); err != nil {
		// We don't want to fail when the file is smaller than the 512 bytes needed to sniff
		// its media type. This can happen with non-binary content (eg. a small Python script).
		if err != io.ErrUnexpectedEOF {
			return "", err
		}
	}
	return http.DetectContentType(sniffBuf), nil
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
