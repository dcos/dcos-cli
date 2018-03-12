package config

import (
	"crypto/x509"
	"testing"

	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestMarshal(t *testing.T) {
	conf := New()
	conf.SetURL("https://dcos.example.com")
	conf.SetACSToken("token_XYZ")
	conf.SetTLS(TLS{})
	conf.SetTimeout(15)
	conf.SetSSHUser("dcos-user")
	conf.SetSSHProxyHost("dcos-bastion")
	conf.SetPagination(true)
	conf.SetReporting(true)
	conf.SetMesosMasterURL("https://mesos.example.com")
	conf.SetPromptLogin(true)
	conf.SetClusterName("custom-cluster-name")

	store := NewStore(StoreOpts{})
	Marshal(&conf, store)

	require.Equal(t, "https://dcos.example.com", store.Get(keyURL))
	require.Equal(t, "true", store.Get(keyTLS))
	require.EqualValues(t, 15, store.Get(keyTimeout))
	require.Equal(t, "dcos-user", store.Get(keySSHUser))
	require.Equal(t, "dcos-bastion", store.Get(keySSHProxyHost))
	require.Equal(t, true, store.Get(keyPagination))
	require.Equal(t, true, store.Get(keyReporting))
	require.Equal(t, "https://mesos.example.com", store.Get(keyMesosMasterURL))
	require.Equal(t, true, store.Get(keyPrompLogin))
	require.Equal(t, "custom-cluster-name", store.Get(keyClusterName))
}

func TestMarshalTLS(t *testing.T) {
	require.Equal(t, "true", marshalTLS(TLS{}))
	require.Equal(t, "false", marshalTLS(TLS{Insecure: true}))
	require.Equal(t, "/path/to/ca", marshalTLS(TLS{RootCAsPath: "/path/to/ca"}))
}

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
		tlsConfig := unmarshalTLS(exp.val)
		require.Equal(t, exp.insecure, tlsConfig.Insecure)
	}
}

func TestUnmarshalTLSWithValidCA(t *testing.T) {
	ca := []byte(`
-----BEGIN CERTIFICATE-----
MIIDszCCApugAwIBAgIQcaz0cEq1THqqPyMRUq6YADANBgkqhkiG9w0BAQsFADCB
ijELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMRYwFAYDVQQHDA1TYW4gRnJhbmNp
c2NvMRkwFwYDVQQKDBBNZXNvc3BoZXJlLCBJbmMuMTswOQYDVQQDDDJEQy9PUyBS
b290IENBIDIwMWMzZTlhLWUzZWUtNDc0MC1hZWUzLWJmMTJjMDBjYWUzMzAeFw0x
ODAzMDcwNzE1MDFaFw0yODAzMDQwNzE1MDFaMIGKMQswCQYDVQQGEwJVUzELMAkG
A1UECAwCQ0ExFjAUBgNVBAcMDVNhbiBGcmFuY2lzY28xGTAXBgNVBAoMEE1lc29z
cGhlcmUsIEluYy4xOzA5BgNVBAMMMkRDL09TIFJvb3QgQ0EgMjAxYzNlOWEtZTNl
ZS00NzQwLWFlZTMtYmYxMmMwMGNhZTMzMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A
MIIBCgKCAQEA36+QojAQvnJhCVeaRCeA/kC70j62OvnecaE/VYI9DkaQAgibTO/z
V99Vz+tUQMfJRuWVd4BSImZ7vOixewU5+jKgcqjuAq7lDuNNX+yz4uYkz67oaBrV
cFvHLmrqDKWeAc8EhsJIscquUCvqGuXdemjvaN22hh09GUqs1N+fMbiZUYmifOJY
+xVE62hD1U2h0FJdPHbnVmIvev7LZ7R90qoFHmNTqdkkT8Q2QkdHpcm3+bxxrtVI
7Mgf50xvLwd7pHMs60caduPIAX5PHs8BFcwYwTSt2QTWlcT2bNsBxCxwFlspCOqb
+VdKTWftDJbzTvarmo3U07i5C0BJJ0MjUQIDAQABoxMwETAPBgNVHRMBAf8EBTAD
AQH/MA0GCSqGSIb3DQEBCwUAA4IBAQB+iINvE921xcAqHo4s/4NfByNhH/XYnAyn
vfGPvb2I8ijoaj2Iab2FCrt9SdCcYQd+RPwwbe3ByPKvgSSzw/IpmniSlJ6+cKo+
cmwLp2NVvFE73YDsq5mbo3T7Zb5E7SMTWWq7fZsWFOVMA2AML6n2DcQzzjjDRdBQ
ItsQvDefqA5fNDB5LepftYbCNuk65ONGyCjpIoAw+reyzYMJorkG5Sb7AJIyFh2/
XG3O73Yy5lml6cOyz0iaX46ZaMdm+YEvisSdYGG75uX/ilEOvQObi0vUfM5f6asL
NT4Sf75bbjkawxsKnddRgK2dILw//sQdOXmSJboaStNrHS5joczy
-----END CERTIFICATE-----
`)
	f, _ := afero.TempFile(fs, "/", "ca")
	f.Write(ca)

	tlsConfig := unmarshalTLS(f.Name())
	require.Equal(t, false, tlsConfig.Insecure)
	require.Equal(t, f.Name(), tlsConfig.RootCAsPath)

	certPool := x509.NewCertPool()
	require.True(t, certPool.AppendCertsFromPEM(ca))
	require.Equal(t, certPool, tlsConfig.RootCAs)
}
