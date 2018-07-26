package log

import (
	"bytes"
	"io/ioutil"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/sirupsen/logrus"
)

func TestFormat(t *testing.T) {
	formatter := &Formatter{}
	logger := &logrus.Logger{
		Out:       ioutil.Discard,
		Formatter: formatter,
	}

	fixtures := []struct {
		entry  *logrus.Entry
		expOut string
	}{
		{
			// simple entry
			&logrus.Entry{
				Logger:  logger,
				Message: "DEBUGME",
			},
			"DEBUGME\n",
		},
		{
			// entry with buffer
			&logrus.Entry{
				Logger:  logger,
				Message: "DEBUGMETOO",
				Buffer:  bytes.NewBuffer(nil),
			},
			"DEBUGMETOO\n",
		},
	}

	for _, fixture := range fixtures {
		out, err := formatter.Format(fixture.entry)
		require.NoError(t, err)
		require.Equal(t, fixture.expOut, string(out))
	}
}
