package log

import (
	"bytes"

	"github.com/sirupsen/logrus"
)

// Formatter is a simple formatter for logrus.
type Formatter struct{}

// Format returns the log entry message with a trailing newline.
func (f *Formatter) Format(entry *logrus.Entry) ([]byte, error) {
	var b *bytes.Buffer
	if entry.Buffer != nil {
		b = entry.Buffer
	} else {
		b = &bytes.Buffer{}
	}
	b.WriteString(entry.Message + "\n")
	return b.Bytes(), nil
}
