// Code generated by go-bindata DO NOT EDIT.
// sources:
// completion.sh
package completion

import (
	"bytes"
	"compress/gzip"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func bindataRead(data []byte, name string) ([]byte, error) {
	gz, err := gzip.NewReader(bytes.NewBuffer(data))
	if err != nil {
		return nil, fmt.Errorf("Read %q: %v", name, err)
	}

	var buf bytes.Buffer
	_, err = io.Copy(&buf, gz)
	clErr := gz.Close()

	if err != nil {
		return nil, fmt.Errorf("Read %q: %v", name, err)
	}
	if clErr != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

type asset struct {
	bytes []byte
	info  os.FileInfo
}

type bindataFileInfo struct {
	name    string
	size    int64
	mode    os.FileMode
	modTime time.Time
}

func (fi bindataFileInfo) Name() string {
	return fi.name
}
func (fi bindataFileInfo) Size() int64 {
	return fi.size
}
func (fi bindataFileInfo) Mode() os.FileMode {
	return fi.mode
}
func (fi bindataFileInfo) ModTime() time.Time {
	return fi.modTime
}
func (fi bindataFileInfo) IsDir() bool {
	return false
}
func (fi bindataFileInfo) Sys() interface{} {
	return nil
}

var _completionSh = []byte("\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff\xec\x5b\x6d\x6f\x1b\x37\x12\xfe\x7c\xfa\x15\xd3\x95\x80\xd8\x8e\xb7\x49\xbe\xda\xa7\x20\xbd\xbc\x1c\x02\xb4\x4d\x71\xbd\x7e\x38\x18\x86\xc0\xe5\xce\x6a\x79\xa6\xc8\x05\x5f\xa4\xe8\x7c\xfe\xef\xc5\x90\xfb\x2e\xd9\x4d\x5a\x39\x4e\x51\x0b\x08\x2c\x73\xc9\x99\xe1\xcc\x33\xcf\x90\xeb\xc9\xf4\x9b\x67\x99\x50\xcf\x32\x66\xcb\xc9\x64\x0a\x8b\x45\xce\xb5\x5d\xfc\xbd\x44\x59\xa1\x81\xc2\x2b\xfe\x92\x86\xe3\x28\x97\x02\xac\xcf\xb8\x5e\xad\x98\xca\x5f\x4e\x26\xf5\xf4\x1c\x33\xbf\x3c\x3a\x86\xeb\x09\x00\x80\x28\xe0\xe2\x02\x52\x05\xb3\xeb\x37\xaf\x3f\xfc\xbc\x78\xfd\xe1\x87\x9f\x16\x6f\xde\xfe\xe3\x97\x7f\x2e\xde\xbd\xff\xfe\xed\x0d\x5c\x5e\x9e\x83\x2b\x51\x85\xd9\xf4\x41\x5e\x6a\x48\x66\xd7\xef\x7e\xf9\xf1\xf5\x8f\xdf\xfd\xf0\xf6\xe2\xc5\xe5\xcd\x19\xcc\x4e\x12\x78\xf9\x92\xc6\xf7\x8a\x49\xc2\xf2\x42\x4c\x6e\x60\x42\xa6\xbf\xc1\x82\x79\xe9\x20\xc3\x92\xad\x85\x36\xe0\x34\x2c\xd1\x91\x26\x50\xf8\xd1\x41\x6d\x36\x14\x46\xaf\xc2\x28\xf7\xc6\xa0\x6a\x1f\x7c\x0b\xef\x55\x1c\x67\x16\x41\x17\x90\xa6\xe4\x06\xa0\x35\x2b\xb6\xcd\x10\xb4\x2b\xd1\x80\x15\xce\x33\x27\xb4\xb2\x93\x29\x88\xb8\xa4\xf0\xce\x1b\x04\x57\x32\x07\xb6\xd4\x5e\xe6\x80\x2a\x27\xc9\x95\x44\x9a\x7b\x0a\xae\x14\x16\x0c\x3a\x6f\x94\x85\x17\xa7\x51\xd8\x46\x58\x84\xe7\x93\xe9\x64\x0a\xdf\x59\xeb\x57\x68\x81\xc1\xac\xb1\x74\xcd\x8c\x60\x99\x44\xc0\x8f\xc2\x3a\xdb\x28\xe3\x4c\x4a\xa1\x96\xc0\xb5\x72\xb4\xb1\xa0\x75\x23\xa4\x0c\x23\xac\x31\x49\x7b\x95\xf7\xc2\x35\x52\xf1\x59\xc2\x85\xed\x3b\x6c\x32\x85\x8d\x36\x39\x64\x48\x13\x71\xcd\xa4\x67\x0e\x7b\x8e\x15\xaa\xf2\x0e\xac\x33\xf4\xfc\x28\x6c\x5c\x58\xc8\xb1\x10\x0a\x73\x52\x54\xe3\x66\x45\xb6\x5a\x5d\x7b\x4c\x3d\xa1\xe0\x01\x83\xca\xe8\x4c\xe2\xea\xb8\x83\x57\x88\xec\xa2\xde\xc8\xa2\x62\xc6\x62\x0b\xb7\x4d\x29\x24\xc2\x05\x24\x33\x9e\x40\x2a\x1d\x7d\x21\xf3\x12\xb8\x3c\x87\x5c\xb7\x20\x13\xf3\x64\x76\x4d\x0f\xec\x05\xbf\xac\xd1\x43\x9f\x10\xed\x64\x26\x12\x10\x1d\x22\xe9\x13\xc3\xff\xff\xb4\x3c\x1e\x0c\xd3\x67\x4a\x20\x0f\xe0\x10\xe4\xcd\x42\xb2\xe5\x29\x70\x9d\x19\x06\xd6\xe9\xca\x02\x99\x48\x9b\x17\xab\x15\xe6\x82\x39\x94\x5b\xda\xe8\x06\x6b\x04\x40\x89\x06\x77\xc4\xd6\xcf\x5e\xec\x3c\x38\x3f\x1f\x5a\x76\x72\x3c\x1e\x3a\xd9\x35\xb2\x76\xd7\x9c\xf6\x76\xbe\x67\x0b\x33\x4e\xd6\x63\x51\x20\x77\x62\x4d\x16\x2e\xa5\xce\x98\x24\x43\x23\xa4\xd8\x16\x84\x03\xce\x14\x70\xc3\x36\x12\x5c\x69\xb4\x5f\x96\x21\xc6\xcc\x2c\xfd\x0a\x95\xb3\xc0\x22\x38\x2a\xa3\x97\x86\xad\xf6\x28\x52\x6c\x2d\x96\xcc\xa1\xad\x53\x45\x71\xca\x08\x70\x06\x31\x24\x97\xd5\x64\x4b\x00\x30\x93\x1b\xb6\xb5\x04\x83\x36\x6d\xbd\x32\xc8\xf2\x80\xb8\x3d\xb2\x59\xe1\x88\xa7\x84\xca\xc9\xdd\xe3\x5c\x3f\x25\x8f\x0b\xc5\x0d\x92\xa9\xa4\x25\xc3\x42\x1b\x84\xcc\x20\xbb\xa2\x15\xda\x3b\x4a\x75\x5a\x28\xb5\xae\x76\x34\x1c\x1d\xf1\xa7\x4f\x8f\x77\x9d\x1b\x04\xdc\x15\x27\xb4\x8c\x4f\xf6\x49\xc9\xb5\x8a\x91\xaf\xa3\xfd\x7c\x72\xd3\x12\x69\xc9\x54\x2e\x91\x80\x5e\x19\xac\xe4\xb6\x05\x79\x9f\x68\x21\xe9\x68\xc5\x06\x9a\x9c\x84\x39\x52\x73\x26\x41\xcc\x9f\xc7\x5f\x0b\x6d\x7a\xfc\x43\x59\x97\xcc\x5e\x25\x83\x94\x98\x42\x21\x24\xf9\x8f\xbc\xd0\x13\x4a\x39\xc5\x4b\xb2\xf4\x89\x83\x15\x73\xbc\x1c\xf0\xe5\x20\x14\x91\xed\x67\x3d\x4d\xf3\x39\xa5\xa0\x37\xc9\xc9\x2e\xd3\x47\xad\xbc\x44\x7e\x45\x2b\x83\xd4\x6e\xa5\x2e\x0a\x34\xc4\x10\x4d\x52\x45\x1c\x32\xce\xb1\x22\xa0\xa9\x16\x75\xb5\x85\xc2\xc2\x8a\x99\x2b\xcc\x21\xdb\xd2\xe3\xf9\x48\x91\x28\xc0\xea\x53\x60\x60\x2b\xc6\x91\xa6\x2b\x4d\x3b\x52\x9e\x49\xb9\x05\x96\xe7\x98\x83\x15\x8a\x47\xbc\x79\x8b\x26\xe4\xc4\xc7\x0a\x39\x31\x9a\xd3\x34\x07\x0a\x6f\x02\xf3\x07\x5e\x1b\xa8\xa8\xc9\xa3\xdb\xc3\x0e\x8b\x40\x60\x92\x93\xf9\x9e\x04\xa5\x0f\x55\xb5\x7f\xbd\xfd\xe9\xfb\xff\x5c\x88\xa7\x4f\x2f\xe7\x03\x51\x7b\x17\x9c\xef\xa6\xf2\xe7\x8b\x86\x4f\x92\x3d\x80\x70\x21\x3a\xf4\xde\x50\xbd\x7d\xcd\xa4\xb4\x31\xdb\xba\x22\x43\x71\xd0\xde\xf4\xab\xc8\x1a\x55\x00\xd5\xb7\x93\x29\xfc\xfb\xc3\x9b\x0f\x67\x5d\x10\x03\xdc\xc3\x34\xa6\x02\xeb\xb3\x4c\x6e\x29\xf9\x49\x0b\xac\x28\x51\xf1\x63\x25\x05\x17\x4e\x6e\x69\x39\x55\x12\x56\x17\xb1\x58\xe3\xa4\xd4\x1b\x92\xd0\x54\x33\x1b\xcb\xd9\xb8\x9a\x59\xae\xab\x48\x36\xcc\x10\xe4\x8c\x41\xee\xce\x26\xd3\x86\x28\x2c\x59\x65\xd8\x96\xb8\xa0\xdb\x8d\x8d\x45\xbb\x65\xac\x52\xcb\xdc\x76\x8b\xce\x1a\xfc\x86\x9d\x3b\x1d\xb4\x81\x50\x4e\x8f\xf2\xb9\x93\x18\x12\x7a\xd2\x82\x93\xb5\xab\x37\xcc\xc2\x52\xac\x51\x9d\xd6\xd9\x11\xeb\x6e\x28\xbd\x84\x7b\xee\x3c\x93\xed\x6c\xfa\x17\x94\x05\x26\xb6\x56\x73\x11\x2b\x70\x6d\x69\x47\x00\xab\x3c\x66\xfe\x75\xb3\xa5\x8b\x57\x97\x37\x43\x16\x68\x32\x78\x95\xd7\xa9\x1b\x67\x26\xfb\xb3\x77\xc8\x44\xe3\x43\xc6\x59\x90\x53\x13\x52\xf3\x89\xc4\xd4\x03\x09\x81\xa6\xa9\xe6\xa3\x8c\xb5\x1b\x56\x41\x4a\x36\xb7\x31\x50\x8c\xc2\x4d\xbb\x59\x0c\x26\x77\x02\xe7\xed\xf6\x9e\x3d\x4b\x9f\x2d\x6e\x26\x77\x58\xdc\x20\x82\xc2\xd4\x45\x76\x76\x2d\x99\x6d\x6d\xba\x59\xcc\xae\x3b\xe9\x37\xc3\x64\xe9\x1b\x3f\xbf\x73\xdd\xd0\x09\xbd\x79\xf3\xd9\xc0\x03\x83\x79\xb3\x5b\x9d\x13\xeb\xc5\x6d\x09\x19\x37\xc9\xbc\x2b\x03\xc6\xfe\x56\x57\x03\x18\x28\x11\x05\x7c\x03\x77\x9d\xaa\x46\x01\xef\xa9\x2c\x44\xbf\xca\x34\xc1\x99\x1f\x25\x52\x58\x97\x56\x46\xaf\x45\x8e\xc6\x26\x90\x48\xbd\x14\x2a\xfe\xd4\xde\x25\xc7\xbd\x65\xc4\xe9\xb4\x26\x1e\xad\x92\xe3\xd6\xaa\x0b\x48\xff\x37\x80\xde\xc8\x90\x86\x67\xbd\xd9\x73\x4c\xdb\xc3\x7f\xb7\xd4\x53\x4a\x84\x60\x43\xc8\x82\xdf\x3a\x66\x7d\x9e\xdc\x41\x82\x7d\xf2\xc9\x60\x8f\x87\x6f\xe3\x8e\x61\x94\x17\xc1\xcd\x5f\x22\xd6\x75\xd0\xa0\x89\x5a\x78\x94\xa4\x69\xc5\xac\xa5\xa3\xc0\x7c\x67\x24\x2d\x84\xc4\xde\xb0\x11\x6b\xe6\x30\xbd\xc2\x6d\x7f\x30\x22\xa6\x1b\xa1\xea\x4b\xb9\x5e\x8f\x1c\x0a\x1c\xfb\x2a\xef\xb4\x3e\xdb\x58\x5f\x55\xda\xb8\x78\xd6\x68\xcb\x52\xaf\x4e\x6e\xd1\xdd\x72\x4a\xff\xcd\x33\xfa\x3d\xc2\xf2\x53\xd1\x34\x02\x8c\xb0\x6e\xd1\x26\xea\x17\x44\x4e\x03\x1c\x0a\xf2\x7f\xad\x56\x07\xcb\xfb\xbf\x6e\x68\x77\xa8\x40\x7b\xf7\x00\x11\x7d\x0c\xe4\xc1\x02\xc9\xa5\xb7\x0e\x4d\x7b\xe3\x3b\x60\x1c\xe1\xee\x02\xce\x9c\x63\xbc\x4c\x20\xa9\x93\x94\x78\x22\x81\xc4\xe0\x4a\xaf\x31\x7c\x21\x56\x4e\x20\xb1\xe8\x7c\xf5\x58\xcf\xc7\xa2\xff\x78\x3d\xaf\x63\xbf\x88\x91\xb8\x0f\x08\x3c\xa6\xf2\x97\x4f\xe5\x50\x70\x1f\x26\x98\x54\x69\x23\x98\x30\x7f\x2c\xbb\xf7\x18\xe2\x48\x92\x0f\x18\x64\x29\xc3\x4f\xaf\xd8\x9a\x09\xc9\x32\x89\x8f\x61\xbe\x8f\x30\x53\x09\xfc\x73\x13\xf3\x57\xe7\xd4\x70\x9c\x78\x18\x9f\xb6\x0b\x92\x34\xe5\x2c\xe5\x68\x9c\x9d\x0f\x46\x85\xb2\xc8\xbd\xc1\xc1\x60\xef\x76\xda\x8c\xe8\x34\xbc\xae\x1b\x0f\x56\xd2\x2f\x85\x1a\x8c\x8e\xae\xcb\x70\xfb\x95\x19\x6e\xbb\x36\xc3\xde\xab\x33\x3c\x5e\x9f\xef\x19\xb0\x5a\x15\x62\xf9\x00\x27\x73\x8b\x74\x10\xb7\xa5\xde\x24\x90\x78\x45\xbf\x3e\x9e\xbe\xe1\xe0\xa7\xef\x10\x5e\xa2\xa3\x2f\x15\xe2\x3f\x5b\xe0\x7e\x5f\xc2\x2c\x08\xb8\x8f\x2e\x3d\xa8\x4b\x03\x09\x3c\xfa\xf4\x30\x3e\x8d\x45\xfa\x21\xde\xb8\xe4\xf9\xce\x7b\x96\x47\x62\x87\x43\x13\x7b\x8c\xef\x82\xe5\xf9\x03\x65\x4c\x38\x96\x55\x39\x73\x87\xbb\x94\x7d\x65\xc9\x73\x6f\xef\x38\x3e\xd1\xbb\x07\x7d\xaf\xf1\xb5\xf9\xf6\xfe\x5e\x2e\xfc\x05\xd9\x7e\xf4\xd7\x91\xf9\x8b\xfb\xff\xcb\x38\xf3\xae\x4c\x20\xa9\xef\xbb\xf4\x2d\x14\xf1\xee\x4d\x7b\x7d\x4b\xbc\x83\xfa\x09\xe3\x6b\x34\x56\x74\x30\x6f\xbb\x68\xf2\x1c\xa2\x80\xae\x55\xc2\xa0\xc4\x35\x53\x2e\x34\xa3\xc4\x6e\x2d\xb9\x85\xe6\x4d\x20\xd4\x96\x34\x72\x94\xee\x37\x65\x34\xdd\x27\xf1\xf6\x86\x80\x22\xf4\x3c\x05\x83\x40\x9b\x7e\x5b\xcc\x1f\x44\xc6\x9e\x5b\x65\xb3\xa9\x3d\xf7\xca\xde\x75\xd2\x88\x65\xe9\x40\xe9\xcd\x68\x6d\xe8\xd2\xc9\x35\x5a\x90\xc8\xd6\x18\xda\xd9\x42\x4b\xa2\x76\xa8\x9c\x20\xb7\x6a\x03\x39\x3a\xe4\x4e\xa8\x65\xbd\xa7\xd0\x61\xe3\xd8\x15\xc2\x9a\x49\x8f\x16\x32\xef\x42\x7b\x90\xc5\x8a\x99\xd0\x4f\x23\xc5\x15\x8e\x74\xa5\x69\xb0\x2a\x2c\x01\xa1\xac\x43\x96\xc7\x66\x61\x1a\x9f\x87\xf1\xd1\x92\x0d\x3e\x31\x18\x3a\xcf\x36\xda\x98\x2d\x59\xc0\x32\xb2\xb1\xb9\x37\x8f\xae\xcc\xe0\xca\xd0\x66\x69\x35\x08\xf7\xc4\x82\x65\x05\x52\x44\xc5\x52\xe9\xba\xc9\x78\xa0\x61\xcf\x8d\xba\x97\x1b\x84\xa3\xe3\xcf\x98\xbf\x93\xb3\x9f\x9f\xaf\x3d\x69\x3b\x71\x56\x7a\xb7\xe7\x89\x76\x4a\x85\x24\x04\xae\xd2\xd6\x8a\x4c\xe2\x0e\xe0\x9a\xcf\x48\xa0\x50\x60\x90\x49\xf0\x96\x2d\xf1\xb4\x6b\x9e\xae\xfb\x49\xad\x0e\x9d\xd8\xbe\xaa\xdb\x95\xfb\xbd\xab\xb5\x76\xa7\xfb\x8d\x5c\xa7\x21\x52\xd6\x1b\xdc\x79\x7d\x31\x85\x52\x6f\x60\x83\xb0\xa9\x73\x2c\xfa\x64\x37\x22\xbf\xeb\xfc\x73\xa8\xb3\x4f\xd7\x5b\x7d\x4b\xfb\xe8\xec\xd5\xa0\x63\x94\x7b\x03\x95\xc1\x75\xe8\xeb\xb4\x10\x9a\xa7\x07\xed\x4a\x35\x5d\x90\xb3\x06\xe3\xc1\x6b\x46\x6b\x47\xcb\x0b\xf1\x31\xca\xec\xf7\x39\x25\x41\x6f\xad\xad\xed\x47\x9c\x1f\xb5\x54\x36\xec\xaf\x1b\x76\xa2\x67\xcc\x96\x69\x2f\x33\x2a\xc6\xaf\xd8\x12\xeb\xd6\xcf\xf7\x90\xa1\x14\xb8\x46\x58\x79\xeb\x6a\x71\x59\x4c\x49\x26\x25\xe6\x6d\x1a\xcb\x6d\xec\x4c\x0f\xff\xc7\x21\x78\x63\x89\xc1\xc4\x6a\x11\x76\xbc\xc8\xb6\x0b\x83\x05\xa4\x0a\x92\xf9\x59\xb2\xd7\x1f\x93\x3d\x6e\xfc\xd9\x31\xe3\x62\x93\x63\xd7\xc1\xaa\x80\xe8\x2e\x2a\x6c\xda\xcd\x4f\x28\xd2\x51\x00\xad\xa7\x20\xb5\x2c\x9b\xea\x60\x57\x5d\x72\xe8\xd7\xde\x57\xa5\x63\xdf\x6a\xfa\x6e\xd0\x31\x1f\x84\xfc\x1a\x00\x00\xff\xff\x1e\x52\x1a\x9b\xb9\x31\x00\x00")

func completionShBytes() ([]byte, error) {
	return bindataRead(
		_completionSh,
		"completion.sh",
	)
}

func completionSh() (*asset, error) {
	bytes, err := completionShBytes()
	if err != nil {
		return nil, err
	}

	info := bindataFileInfo{name: "completion.sh", size: 0, mode: os.FileMode(0), modTime: time.Unix(0, 0)}
	a := &asset{bytes: bytes, info: info}
	return a, nil
}

// Asset loads and returns the asset for the given name.
// It returns an error if the asset could not be found or
// could not be loaded.
func Asset(name string) ([]byte, error) {
	cannonicalName := strings.Replace(name, "\\", "/", -1)
	if f, ok := _bindata[cannonicalName]; ok {
		a, err := f()
		if err != nil {
			return nil, fmt.Errorf("Asset %s can't read by error: %v", name, err)
		}
		return a.bytes, nil
	}
	return nil, fmt.Errorf("Asset %s not found", name)
}

// MustAsset is like Asset but panics when Asset would return an error.
// It simplifies safe initialization of global variables.
func MustAsset(name string) []byte {
	a, err := Asset(name)
	if err != nil {
		panic("asset: Asset(" + name + "): " + err.Error())
	}

	return a
}

// AssetInfo loads and returns the asset info for the given name.
// It returns an error if the asset could not be found or
// could not be loaded.
func AssetInfo(name string) (os.FileInfo, error) {
	cannonicalName := strings.Replace(name, "\\", "/", -1)
	if f, ok := _bindata[cannonicalName]; ok {
		a, err := f()
		if err != nil {
			return nil, fmt.Errorf("AssetInfo %s can't read by error: %v", name, err)
		}
		return a.info, nil
	}
	return nil, fmt.Errorf("AssetInfo %s not found", name)
}

// AssetNames returns the names of the assets.
func AssetNames() []string {
	names := make([]string, 0, len(_bindata))
	for name := range _bindata {
		names = append(names, name)
	}
	return names
}

// _bindata is a table, holding each asset generator, mapped to its name.
var _bindata = map[string]func() (*asset, error){
	"completion.sh": completionSh,
}

// AssetDir returns the file names below a certain
// directory embedded in the file by go-bindata.
// For example if you run go-bindata on data/... and data contains the
// following hierarchy:
//     data/
//       foo.txt
//       img/
//         a.png
//         b.png
// then AssetDir("data") would return []string{"foo.txt", "img"}
// AssetDir("data/img") would return []string{"a.png", "b.png"}
// AssetDir("foo.txt") and AssetDir("notexist") would return an error
// AssetDir("") will return []string{"data"}.
func AssetDir(name string) ([]string, error) {
	node := _bintree
	if len(name) != 0 {
		cannonicalName := strings.Replace(name, "\\", "/", -1)
		pathList := strings.Split(cannonicalName, "/")
		for _, p := range pathList {
			node = node.Children[p]
			if node == nil {
				return nil, fmt.Errorf("Asset %s not found", name)
			}
		}
	}
	if node.Func != nil {
		return nil, fmt.Errorf("Asset %s not found", name)
	}
	rv := make([]string, 0, len(node.Children))
	for childName := range node.Children {
		rv = append(rv, childName)
	}
	return rv, nil
}

type bintree struct {
	Func     func() (*asset, error)
	Children map[string]*bintree
}
var _bintree = &bintree{nil, map[string]*bintree{
	"completion.sh": &bintree{completionSh, map[string]*bintree{}},
}}

// RestoreAsset restores an asset under the given directory
func RestoreAsset(dir, name string) error {
	data, err := Asset(name)
	if err != nil {
		return err
	}
	info, err := AssetInfo(name)
	if err != nil {
		return err
	}
	err = os.MkdirAll(_filePath(dir, filepath.Dir(name)), os.FileMode(0755))
	if err != nil {
		return err
	}
	err = ioutil.WriteFile(_filePath(dir, name), data, info.Mode())
	if err != nil {
		return err
	}
	err = os.Chtimes(_filePath(dir, name), info.ModTime(), info.ModTime())
	if err != nil {
		return err
	}
	return nil
}

// RestoreAssets restores an asset under the given directory recursively
func RestoreAssets(dir, name string) error {
	children, err := AssetDir(name)
	// File
	if err != nil {
		return RestoreAsset(dir, name)
	}
	// Dir
	for _, child := range children {
		err = RestoreAssets(dir, filepath.Join(name, child))
		if err != nil {
			return err
		}
	}
	return nil
}

func _filePath(dir, name string) string {
	cannonicalName := strings.Replace(name, "\\", "/", -1)
	return filepath.Join(append([]string{dir}, strings.Split(cannonicalName, "/")...)...)
}
