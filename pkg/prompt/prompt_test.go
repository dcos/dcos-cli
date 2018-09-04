package prompt

import (
	"bytes"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestInput(t *testing.T) {
	var buf bytes.Buffer
	prompt := New(strings.NewReader("this\n"), &buf)
	val := prompt.Input("What do you write? ")
	require.Equal(t, "What do you write? ", buf.String())
	require.Equal(t, "this", val)
}

func TestPassword(t *testing.T) {
	var buf bytes.Buffer
	prompt := New(strings.NewReader("pass\n"), &buf)
	val := prompt.Input("Password:")
	require.Equal(t, "Password:", buf.String())
	require.Equal(t, "pass", val)
}

func TestSelect(t *testing.T) {
	fixtures := []struct {
		input         string
		expectError   bool
		expectedValue int
	}{
		{"-1\n", true, 0},
		{"0\n", true, 0},
		{"1\n", false, 0},
		{"2\n", false, 1},
		{"3\n", false, 2},
		{"4\n", true, 0},
	}

	for _, fixture := range fixtures {
		var buf bytes.Buffer
		prompt := New(strings.NewReader(fixture.input), &buf)

		i, err := prompt.Select("Please choose:", []string{"a", "b", "c"})
		if fixture.expectError {
			require.Error(t, err)
		} else {
			require.NoError(t, err)
			require.Equal(t, fixture.expectedValue, i)
		}

	}
}

func TestConfirm(t *testing.T) {
	fixtures := []struct {
		input         string
		defaultChoice string
		expectError   bool
	}{
		{"", "", true},
		{"Y\n", "", false},
		{"Y\r\n", "", false},
		{"yes\n", "", false},
		{"yes\r\n", "", false},
		{"y\n", "", false},
		{"\n\nY\n", "", false},
		{"N\n", "", true},
		{"no\n", "", true},
		{"n\n", "", true},
		{"n\r\n", "", true},
		{"\n", "yes", false},
		{"\n", "no", true},
	}

	for _, fixture := range fixtures {
		var buf bytes.Buffer
		prompt := New(strings.NewReader(fixture.input), &buf)

		err := prompt.Confirm("Please confirm:", fixture.defaultChoice)
		if fixture.expectError {
			require.Error(t, err)
		} else {
			require.NoError(t, err)
		}
	}
}
