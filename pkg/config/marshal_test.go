package config

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestUnmarshalTLS(t *testing.T) {
	expectedTLSInsecureSkipVerify := []struct {
		val      interface{}
		insecure bool
	}{
		{"True", false},
		{"1", false},
		{"true", false},
		{"False", true},
		{"false", true},
		{"0", true},
		{"/path/to/unexisting/ca", true},
	}

	for _, exp := range expectedTLSInsecureSkipVerify {
		tlsConfig := UnmarshalTLS(exp.val)
		require.NotNil(t, tlsConfig)
		require.Equal(t, exp.insecure, tlsConfig.Insecure)
	}
}
