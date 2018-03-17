package config

import (
	"crypto/x509"
	"io"
	"strconv"
	"strings"
	"time"

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
	conf.store.SetPath(path)
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

	conf := Default()
	Unmarshal(NewStore(StoreOpts{Tree: tree}), &conf)
	return conf, nil
}

// Unmarshal extracts configuration data from the Store and stores it in the Config.
func Unmarshal(store *Store, conf *Config) {
	for _, key := range store.Keys() {
		val := store.Get(key)
		switch key {
		case keyURL:
			conf.url = cast.ToString(val)
		case keyACSToken:
			conf.acsToken = cast.ToString(val)
		case keyTLS:
			conf.tls = unmarshalTLS(val)
		case keyTimeout:
			conf.timeout = time.Duration(cast.ToInt64(val)) * time.Second
		case keySSHUser:
			conf.sshUser = cast.ToString(val)
		case keySSHProxyHost:
			conf.sshProxyHost = cast.ToString(val)
		case keyPagination:
			conf.pagination = cast.ToBool(val)
		case keyReporting:
			conf.reporting = cast.ToBool(val)
		case keyMesosMasterURL:
			conf.mesosMasterURL = cast.ToString(val)
		case keyPrompLogin:
			conf.promptLogin = cast.ToBool(val)
		case keyClusterName:
			conf.clusterName = cast.ToString(val)
		}
	}
	conf.store = store
}

// unmarshalTLS creates a TLS struct from a string.
//
// Valid values are:
// - A path to a root CA bundle.
// - "1", "t", "T", "TRUE", "true", "True" - will use the system's CA bundle.
// - "0", "f", "F", "FALSE", "false", "False" - will send insecure requests.
func unmarshalTLS(val interface{}) TLS {
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

// Marshal updates the Store with Config dirty fields.
func Marshal(conf *Config, store *Store) {
	if conf.dirtyFields[&conf.url] {
		store.Set(keyURL, conf.url)
	}
	if conf.dirtyFields[&conf.acsToken] {
		store.Set(keyACSToken, conf.acsToken)
	}
	if conf.dirtyFields[&conf.tls] {
		store.Set(keyTLS, marshalTLS(conf.tls))
	}
	if conf.dirtyFields[&conf.timeout] {
		store.Set(keyTimeout, conf.timeout.Seconds())
	}
	if conf.dirtyFields[&conf.sshUser] {
		store.Set(keySSHUser, conf.sshUser)
	}
	if conf.dirtyFields[&conf.sshProxyHost] {
		store.Set(keySSHProxyHost, conf.sshProxyHost)
	}
	if conf.dirtyFields[&conf.pagination] {
		store.Set(keyPagination, conf.pagination)
	}
	if conf.dirtyFields[&conf.reporting] {
		store.Set(keyReporting, conf.reporting)
	}
	if conf.dirtyFields[&conf.mesosMasterURL] {
		store.Set(keyMesosMasterURL, conf.mesosMasterURL)
	}
	if conf.dirtyFields[&conf.promptLogin] {
		store.Set(keyPrompLogin, conf.promptLogin)
	}
	if conf.dirtyFields[&conf.clusterName] {
		store.Set(keyClusterName, conf.clusterName)
	}

	// Clear config dirty fields.
	conf.dirtyFields = make(map[interface{}]bool)
}

// marshalTLS creates a string from a TLS struct.
func marshalTLS(tls TLS) string {
	if tls.RootCAsPath != "" {
		return tls.RootCAsPath
	}
	return strconv.FormatBool(!tls.Insecure)
}
