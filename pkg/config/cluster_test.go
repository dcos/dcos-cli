package config

import (
	"crypto/x509"
	"testing"
	"time"

	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestGetters(t *testing.T) {
	conf := Empty()

	conf.Set("core.dcos_url", "https://dcos.example.com")
	conf.Set("core.dcos_acs_token", "token_zj8Tb0vhQw")
	conf.Set("core.timeout", 15)
	conf.Set("cluster.name", "mr-cluster")

	cluster := NewCluster(conf)

	clusterTLS, err := cluster.TLS()

	require.NoError(t, err)
	require.Equal(t, "https://dcos.example.com", cluster.URL())
	require.Equal(t, "token_zj8Tb0vhQw", cluster.ACSToken())
	require.Equal(t, false, clusterTLS.Insecure)
	require.Equal(t, 15*time.Second, cluster.Timeout())
	require.Equal(t, "mr-cluster", cluster.Name())
}

func TestSetters(t *testing.T) {
	conf := Empty()

	cluster := NewCluster(conf)
	cluster.SetURL("https://dcos.example.com")
	cluster.SetACSToken("token_XYZ")
	cluster.SetTLS(TLS{})
	cluster.SetTimeout(15 * time.Second)
	cluster.SetName("custom-cluster-name")

	require.Equal(t, "https://dcos.example.com", conf.Get("core.dcos_url"))
	require.Equal(t, "token_XYZ", conf.Get("core.dcos_acs_token"))
	require.Equal(t, "true", conf.Get("core.ssl_verify"))
	require.EqualValues(t, 15, conf.Get("core.timeout"))
	require.Equal(t, "custom-cluster-name", conf.Get("cluster.name"))
}

func TestTLSToString(t *testing.T) {
	expectedTLSStrings := []struct {
		tls TLS
		str string
	}{
		{TLS{}, "true"},
		{TLS{Insecure: true}, "false"},
		{TLS{RootCAsPath: "/path/to/ca"}, "/path/to/ca"},
	}

	for _, exp := range expectedTLSStrings {
		require.Equal(t, exp.str, exp.tls.String())
	}
}

func TestGetTLS(t *testing.T) {

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
	}

	for _, exp := range expectedTLSInsecureSkipVerify {
		t.Run(exp.val.(string), func(t *testing.T) {
			conf := Empty()
			err := conf.Set("core.ssl_verify", exp.val)
			require.NoError(t, err)
			cluster := NewCluster(conf)
			clusterTLS, err := cluster.TLS()
			require.NoError(t, err)
			require.Equal(t, exp.insecure, clusterTLS.Insecure)
		})
	}
}

func TestSetTLSWithNotExistingFile(t *testing.T) {
	conf := Empty()
	err := conf.Set("core.ssl_verify", "/path/to/unexisting/ca")
	require.Error(t, err)
}

func TestGetTLSWithInvalidCA(t *testing.T) {
	conf := New(Opts{
		Fs: afero.NewMemMapFs(),
	})

	ca := []byte(`
-----BEGIN CERTIFICATE-----
I am no authority.
-----END CERTIFICATE-----
`)
	f, _ := afero.TempFile(conf.Fs(), "/", "ca")
	f.Write(ca)

	err := conf.Set("core.ssl_verify", f.Name())
	require.NoError(t, err)
	cluster := NewCluster(conf)

	tlsConfig, err := cluster.TLS()
	require.Error(t, err)
	require.Contains(t, err.Error(), "cannot decode the PEM root certificate(s) into a cert pool:")
	require.Equal(t, true, tlsConfig.Insecure)
	require.Equal(t, f.Name(), tlsConfig.RootCAsPath)
	require.Nil(t, tlsConfig.RootCAs)
}

func TestGetTLSWithValidCA(t *testing.T) {
	conf := New(Opts{
		Fs: afero.NewMemMapFs(),
	})

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
	f, _ := afero.TempFile(conf.Fs(), "/", "ca")
	f.Write(ca)

	conf.Set("core.ssl_verify", f.Name())
	cluster := NewCluster(conf)

	tlsConfig, err := cluster.TLS()
	require.NoError(t, err)
	require.Equal(t, false, tlsConfig.Insecure)
	require.Equal(t, f.Name(), tlsConfig.RootCAsPath)

	certPool := x509.NewCertPool()
	require.True(t, certPool.AppendCertsFromPEM(ca))
	require.Equal(t, certPool, tlsConfig.RootCAs)
}
