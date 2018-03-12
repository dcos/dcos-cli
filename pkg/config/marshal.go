package config

import (
	"crypto/x509"
	"io"
	"strconv"
	"strings"

	toml "github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"github.com/spf13/cast"
)

// FromPath creates a Config based on a path to a TOML file.
func FromPath(path string) (Config, error) {
	f, err := fs.Open(path)
	if err != nil {
		return Config{}, err
	}
	defer f.Close()

	conf, err := FromReader(f)
	conf.Store().SetPath(path)
	return conf, nil
}

// FromString creates a Config using a string representing the configuration formatted as a TOML document.
func FromString(tomlData string) (Config, error) {
	return FromReader(strings.NewReader(tomlData))
}

// FromReader creates a Config based on an io.Reader.
func FromReader(reader io.Reader) (Config, error) {
	tree, err := toml.LoadReader(reader)
	if err != nil {
		return Config{}, err
	}
	conf := fromStore(NewStore(tree, StoreOpts{}))
	return conf, nil
}

func fromStore(store *Store) Config {
	conf := DefaultConfig()
	Unmarshal(&conf, store)
	conf.store = store
	return conf
}

// Unmarshal extracts configuration data from the Store and stores it in the Config.
func Unmarshal(conf *Config, store *Store) {
	for _, key := range store.Keys() {
		val := store.Get(key)
		switch key {
		case keyURL:
			conf.URL = cast.ToString(val)
		case keyACSToken:
			conf.ACSToken = cast.ToString(val)
		case keyTLS:
			conf.TLS = UnmarshalTLS(val)
		case keyTimeout:
			conf.Timeout = cast.ToInt(val)
		case keySSHUser:
			conf.SSHUser = cast.ToString(val)
		case keySSHProxyIP:
			conf.SSHProxyIP = cast.ToString(val)
		case keyPagination:
			conf.Pagination = cast.ToBool(val)
		case keyReporting:
			conf.Reporting = cast.ToBool(val)
		case keyMesosMasterURL:
			conf.MesosMasterURL = cast.ToString(val)
		case keyPrompLogin:
			conf.PrompLogin = cast.ToBool(val)
		case keyClusterName:
			conf.ClusterName = cast.ToString(val)
		}
	}
}

// UnmarshalTLS creates a TLS struct from a string.
//
// Valid values are:
// - A path to a root CA bundle.
// - "1", "t", "T", "TRUE", "true", "True" - will use the system's CA bundle.
// - "0", "f", "F", "FALSE", "false", "False" - will send insecure requests.
func UnmarshalTLS(val interface{}) TLS {
	strVal := cast.ToString(val)

	// If the string is empty or the value couldn't be casted to a string, use the default TLS config.
	if strVal == "" {
		return TLS{}
	}

	// Try to cast the value to a bool, true means we verify
	// server certificates, false means we skip verification.
	if verify, err := strconv.ParseBool(strVal); err == nil {
		return TLS{
			Insecure: !verify,
		}
	}

	// If the value is not a string representing a bool, it means it's a path to a root CA bundle.
	rootCAsPEM, err := afero.ReadFile(fs, strVal)
	if err != nil {
		return TLS{
			Insecure:    true,
			RootCAsPath: strVal,
		}
	}

	// Decode the PEM root certificate(s) into a cert pool.
	certPool := x509.NewCertPool()
	if !certPool.AppendCertsFromPEM(rootCAsPEM) {
		return TLS{
			Insecure:    true,
			RootCAsPath: strVal,
		}
	}

	// The cert pool has been successfully created, store it in the TLS config.
	return TLS{
		RootCAsPath: strVal,
		RootCAs:     certPool,
	}
}
