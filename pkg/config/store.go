package config

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"sort"
	"strings"

	toml "github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"github.com/spf13/cast"
	"github.com/xeipuuv/gojsonschema"
)

// TOML keys for the DC/OS configuration.
const (
	keyURL            = "core.dcos_url"
	keyACSToken       = "core.dcos_acs_token"
	keyTLS            = "core.ssl_verify"
	keyTimeout        = "core.timeout"
	keySSHUser        = "core.ssh_user"
	keySSHProxyHost   = "core.ssh_proxy_ip"
	keyPagination     = "core.pagination"
	keyReporting      = "core.reporting"
	keyMesosMasterURL = "core.mesos_master_url"
	keyPrompLogin     = "core.prompt_login"
	keyClusterName    = "cluster.name"
)

// Environment variables for the DC/OS configuration.
const (
	envURL      = "DCOS_URL"
	envACSToken = "DCOS_ACS_TOKEN"
	envTLS      = "DCOS_SSL_VERIFY"
	envTimeout  = "DCOS_TIMEOUT"
)

// Errors related to the Store.
var (
	ErrInvalidJSONSchema = errors.New("invalid JSON schema")
	ErrInvalidKey        = errors.New("invalid key specified")
	ErrNoStorePath       = errors.New("no path specified for the config store")
)

// fs is an abstraction for the filesystem. All filesystem operations
// should be done through it instead of the os package.
var fs = afero.NewOsFs()

// StoreOpts are functional options for a Store.
type StoreOpts struct {
	// The TOML tree associated to the store. When not set it defaults to an empty tree.
	Tree *toml.Tree

	// EnvWhitelist is a map of config keys and environment variables. When present,
	// these env vars would take precedence over the values in the toml.Tree.
	EnvWhitelist map[string]string

	// EnvLookup is the function used to lookup environment variables.
	// When not set it defaults to os.LookupEnv.
	EnvLookup func(key string) (string, bool)

	// JSONSchemas is a map of JSON schemas to validate non-core configs against.
	// The map key refers to the config section and the associated value is the JSON schema.
	JSONSchemas map[string]*gojsonschema.Schema
}

// Store is the backend for Config data. It aggregates multiple sources (env vars, TOML document)
// and is able to get/set/unset key(s) in the TOML document.
type Store struct {
	path         string
	tree         *toml.Tree
	envWhitelist map[string]string
	envLookup    func(key string) (string, bool)
	jsonSchemas  map[string]*gojsonschema.Schema
}

// NewStore creates a Store according to a TOML tree and functional options.
func NewStore(opts StoreOpts) *Store {
	if opts.Tree == nil {
		opts.Tree, _ = toml.TreeFromMap(make(map[string]interface{}))
	}

	if opts.EnvWhitelist == nil {
		opts.EnvWhitelist = map[string]string{
			keyURL:      envURL,
			keyACSToken: envACSToken,
			keyTLS:      envTLS,
			keyTimeout:  envTimeout,
		}
	}

	if opts.EnvLookup == nil {
		opts.EnvLookup = os.LookupEnv
	}

	if opts.JSONSchemas == nil {
		opts.JSONSchemas = make(map[string]*gojsonschema.Schema)
	}

	return &Store{
		tree:         opts.Tree,
		envWhitelist: opts.EnvWhitelist,
		envLookup:    opts.EnvLookup,
		jsonSchemas:  opts.JSONSchemas,
	}
}

// SetPath assigns a path to the Store.
func (s *Store) SetPath(path string) {
	s.path = path
}

// Get returns a value from the Store using a key.
func (s *Store) Get(key string) interface{} {
	// Check if the given key is whitelisted as an env var.
	if envVar, ok := s.envWhitelist[key]; ok {
		// If so, look-it up.
		if envVal, ok := s.envLookup(envVar); ok {
			val, _ := s.normalize(key, envVal)
			return val
		}
	}

	// Fallback to the TOML tree if present.
	switch node := s.tree.Get(key).(type) {
	case *toml.Tree, []*toml.Tree, nil:
		return nil
	default:
		val, _ := s.normalize(key, node)
		return val
	}
}

// Set sets a key in the store.
func (s *Store) Set(key string, val interface{}) (err error) {
	val, err = s.normalize(key, val)
	if err == nil {
		s.tree.Set(key, val)
	}
	return err
}

// Unset deletes a given key from the Store.
func (s *Store) Unset(key string) {
	keys := strings.Split(key, ".")

	treeMap := s.tree.ToMap()
	subMap := treeMap

	// Extract a sub-map for each dotted key section.
	for i, key := range keys {
		if node, ok := subMap[key]; ok {
			switch nodeType := node.(type) {
			case map[string]interface{}:
				subMap = nodeType
			default:
				// Abort if the section is not a map, unless it's the last section.
				if i == len(keys)-1 {
					// Remove the key from the parent map and swap trees.
					delete(subMap, key)
					s.tree, _ = toml.TreeFromMap(treeMap)
				} else {
					return
				}
			}
		}
	}
}

// Persist flushes the in-memory TOML tree representation to the path associated to the Store.
func (s *Store) Persist() error {
	if s.path == "" {
		return ErrNoStorePath
	}
	var buf bytes.Buffer
	if _, err := s.tree.WriteTo(&buf); err != nil {
		return err
	}
	return afero.WriteFile(fs, s.path, buf.Bytes(), 0600)
}

// Keys returns all the keys in the Store.
func (s *Store) Keys() []string {
	var keys []string
	for key, envVar := range s.envWhitelist {
		if _, ok := s.envLookup(envVar); ok {
			keys = append(keys, key)
		}
	}

	searchKeys(s.tree, &keys, []string{})
	keysLen := len(keys)
	if keysLen < 2 {
		// Less than 2 keys, no need to sort or remove duplicates.
		return keys
	}

	sort.Strings(keys)

	// Remove duplicates, this happens when there is both an env var and a TOML key.
	// Keys are already sorted so this is done by comparing each key with the next one
	// and removing the latter if it's the same.
	for i := 1; i < keysLen; i++ {
		if keys[i] == keys[i-1] {
			keys = append(keys[:i], keys[i+1:]...)
			keysLen--
			i--
		}
	}
	return keys
}

// searchKeys walks recursively through a toml.Tree and appends the full path to each leaf into keys.
func searchKeys(tree *toml.Tree, keys *[]string, keyPath []string) {
	for _, key := range tree.Keys() {
		childKeyPath := append(keyPath, key)
		switch node := tree.Get(key).(type) {
		case *toml.Tree:
			searchKeys(node, keys, childKeyPath)
		default:
			*keys = append(*keys, strings.Join(childKeyPath, "."))
		}
	}
}

// normalize casts/validates a value for a given config key. For non-core keys it relies
// on JSON schemas. If the casting or validation can't be done it returns an error.
func (s *Store) normalize(key string, val interface{}) (interface{}, error) {
	// Check if it is a core key and cast the value accordingly.
	switch key {
	case
		keyURL,
		keyACSToken,
		keyTLS,
		keySSHUser,
		keySSHProxyHost,
		keyMesosMasterURL,
		keyClusterName:

		return cast.ToStringE(val)
	case keyTimeout:
		return cast.ToInt64E(val)
	case
		keyPagination,
		keyReporting,
		keyPrompLogin:

		return cast.ToBoolE(val)
	}

	keys := strings.SplitN(key, ".", 2)
	if len(keys) != 2 {
		return nil, ErrInvalidKey
	}

	// If it's not a core key, lookup for the section's JSON schema.
	jsonSchema, ok := s.jsonSchemas[keys[0]]
	if !ok {
		// When no JSON schema is defined for a section, return the value as is.
		return val, nil
	}

	// Get the current subtree for the config section. If none create an empty tree.
	subTree, ok := s.tree.Get(keys[0]).(*toml.Tree)
	if !ok {
		subTree, _ = toml.TreeFromMap(make(map[string]interface{}))
	}

	// Set the config value into the tree.
	subTree.Set(keys[1], val)

	// Convert the tree into a map and validate it against the JSON schema.
	result, err := jsonSchema.Validate(gojsonschema.NewGoLoader(subTree.ToMap()))
	if err != nil {
		return nil, ErrInvalidJSONSchema
	}

	// If the result is invalid, iterate through result errors and fail only if the error is for
	// the field we're trying to set. Possible errors about other section fields should be ignored.
	if !result.Valid() {
		for _, err := range result.Errors() {
			if err.Field() == keys[1] {
				return nil, fmt.Errorf("validation error on \"%s\": %s", key, err.Description())
			}
		}
	}
	return val, nil
}
