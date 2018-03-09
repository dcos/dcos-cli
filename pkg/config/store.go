package config

import (
	"os"
	"sort"
	"strings"

	toml "github.com/pelletier/go-toml"
	"github.com/spf13/afero"
	"github.com/spf13/cast"
)

var fs = afero.NewOsFs()

// StoreOpts are functional options for a Store.
type StoreOpts struct {
	// EnvWhitelist is a map of config keys and environment variables. When present,
	// these env vars would take precedence over the values in the toml.Tree.
	EnvWhitelist map[string]string

	// EnvLookup is the function used to lookup environment variables.
	// When not set it defaults to os.LookupEnv.
	EnvLookup func(key string) (string, bool)
}

// Store is the backend for Config data. It aggregates multiple sources (env vars, TOML document)
// and is able to get/set/unset key(s) in the TOML document.
type Store struct {
	tree         *toml.Tree
	envWhitelist map[string]string
	envLookup    func(key string) (string, bool)
}

// NewStore creates a Store according to a TOML tree and functional options.
func NewStore(tree *toml.Tree, opts StoreOpts) *Store {
	if tree == nil {
		tree, _ = toml.TreeFromMap(make(map[string]interface{}))
	}

	if opts.EnvWhitelist == nil {
		opts.EnvWhitelist = map[string]string{
			keyURL:      "DCOS_URL",
			keyACSToken: "DCOS_ACS_TOKEN",
			keyTLS:      "DCOS_SSL_VERIFY",
			keyTimeout:  "DCOS_TIMEOUT",
		}
	}

	if opts.EnvLookup == nil {
		opts.EnvLookup = os.LookupEnv
	}

	return &Store{
		tree:         tree,
		envWhitelist: opts.EnvWhitelist,
		envLookup:    opts.EnvLookup,
	}
}

// Get returns a value from the Store using a key.
func (s *Store) Get(key string) interface{} {
	// Check if the given key is whitelisted as an env var.
	if envVar, ok := s.envWhitelist[key]; ok {
		// If so, look-it up.
		if envVal, ok := s.envLookup(envVar); ok {
			return envVal
		}
	}

	// Fallback to the TOML tree if present.
	if s.tree != nil {
		switch node := s.tree.Get(key).(type) {
		case *toml.Tree, []*toml.Tree:
			return nil
		default:
			return node
		}
	}
	return nil
}

// Set sets a key in the store.
func (s *Store) Set(key string, val interface{}) {
	switch key {
	case keyTimeout:
		// go-toml requires int64
		val = cast.ToInt64(val)
	case keyPagination, keyReporting, keyPrompLogin:
		val = cast.ToBool(val)
	default:
		val = cast.ToString(val)
	}
	s.tree.Set(key, val)
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
