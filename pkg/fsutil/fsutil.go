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
	"strings"

	"github.com/spf13/afero"
)

// CopyDir recursively copies a directory into a given destination.
func CopyDir(fs afero.Fs, src, dest string) error {
	info, err := fs.Stat(src)
	if err != nil {
		return err
	}
	if err := fs.Mkdir(dest, info.Mode()); err != nil {
		return err
	}
	list, err := afero.ReadDir(fs, src)
	if err != nil {
		return err
	}

	for _, entry := range list {
		entrySrc := filepath.Join(src, entry.Name())
		entryDest := filepath.Join(dest, entry.Name())

		if entry.IsDir() {
			err := CopyDir(fs, entrySrc, entryDest)
			if err != nil {
				return err
			}
		} else {
			err := CopyFile(fs, entrySrc, entryDest, entry.Mode())
			if err != nil {
				return err
			}
		}
	}
	return nil
}

// CopyFile copies a file into a given destination.
func CopyFile(fs afero.Fs, src, dest string, perm os.FileMode) error {
	srcFile, err := fs.Open(src)
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
	_, err = io.Copy(destFile, r)
	destFile.Close()
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

	fpath, err := sanitizeExtractPath(dest, f.Name)
	if err != nil {
		return err
	}

	if f.FileInfo().IsDir() {
		return fs.MkdirAll(fpath, f.FileInfo().Mode())
	}

	if err := fs.MkdirAll(filepath.Dir(fpath), 0755); err != nil {
		return err
	}
	return CopyReader(fs, rc, fpath, f.Mode())
}

// see: https://snyk.io/research/zip-slip-vulnerability
func sanitizeExtractPath(destination string, filePath string) (string, error) {
	destpath := filepath.Join(destination, filePath)
	if !strings.HasPrefix(destpath, filepath.Clean(destination)+string(os.PathSeparator)) {
		return "", fmt.Errorf("%s: illegal file path", filePath)
	}
	return destpath, nil
}
