package fsutil

import (
	"os"
	"time"

	"github.com/natefinch/atomic"
	"github.com/spf13/afero"
)

// OsFs is a Fs implementation that uses functions provided by the os package.
//
// For details in any method, check the documentation of the os package
// (http://golang.org/pkg/os/).
type OsFs struct{}

// NewOsFs creates a new Fs.
func NewOsFs() afero.Fs {
	return &OsFs{}
}

// Name returns the name of the filesystem.
func (OsFs) Name() string { return "OsFs" }

// Create creates a file with a given name.
func (OsFs) Create(name string) (afero.File, error) {
	f, e := os.Create(name)
	if f == nil {
		// while this looks strange, we need to return a bare nil (of type nil) not
		// a nil value of type *os.File or nil won't be nil
		return nil, e
	}
	return f, e
}

// Mkdir creates a directory with a given name and permissions.
func (OsFs) Mkdir(name string, perm os.FileMode) error {
	return os.Mkdir(name, perm)
}

// MkdirAll creates a directory named path along with any necessary parents with a given name and permissions.
func (OsFs) MkdirAll(path string, perm os.FileMode) error {
	return os.MkdirAll(path, perm)
}

// Open opens a file with a given name.
func (OsFs) Open(name string) (afero.File, error) {
	f, e := os.Open(name)
	if f == nil {
		// while this looks strange, we need to return a bare nil (of type nil) not
		// a nil value of type *os.File or nil won't be nil
		return nil, e
	}
	return f, e
}

// OpenFile opens a file with given flag and perm.
func (OsFs) OpenFile(name string, flag int, perm os.FileMode) (afero.File, error) {
	f, e := os.OpenFile(name, flag, perm)
	if f == nil {
		// while this looks strange, we need to return a bare nil (of type nil) not
		// a nil value of type *os.File or nil won't be nil
		return nil, e
	}
	return f, e
}

// Remove removes a file/directory with a given name.
func (OsFs) Remove(name string) error {
	return os.Remove(name)
}

// RemoveAll removes a file/directory with a given name.
func (OsFs) RemoveAll(path string) error {
	return os.RemoveAll(path)
}

// Rename rename a file/directory with a given name.
// This is the most important method of this file as it uses Atomic.
func (OsFs) Rename(oldName, newName string) error {
	return atomic.ReplaceFile(oldName, newName)
}

// Stat return the stat of a file with a given name.
func (OsFs) Stat(name string) (os.FileInfo, error) {
	return os.Stat(name)
}

// Chmod return the chmod of a file with a given name.
func (OsFs) Chmod(name string, mode os.FileMode) error {
	return os.Chmod(name, mode)
}

// Chtimes changes the access and modification times of a file with a given name.
func (OsFs) Chtimes(name string, atime time.Time, mtime time.Time) error {
	return os.Chtimes(name, atime, mtime)
}

// LstatIfPossible doas an lstat if possible on a file with a given name.
func (OsFs) LstatIfPossible(name string) (os.FileInfo, bool, error) {
	fi, err := os.Lstat(name)
	return fi, true, err
}
