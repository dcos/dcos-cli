package plugin

import (
	"github.com/spf13/cobra"
)

// Plugin defines an external plugin and its associated data.
type Plugin struct {
	Name        string        `yaml:"name"`
	Description string        `yaml:"description"`
	Version     string        `yaml:"version"`
	Source      source        `yaml:"source"`
	Executables []*executable `yaml:"executables"`

	// Directory containing the plugin's binaries.
	BinDir string

	// Plugin directory in filesystem.
	dir string
}

// executable defines what commands are associated with which executable file in the plugin
type executable struct {
	// Executables are found from pluginDir + Filename. This means all executables in a plugin are in
	// the same place.
	Filename string     `yaml:"filename"`
	Commands []*Command `yaml:"commands"`
}

// Command is a Command living within a plugin binary.
type Command struct {
	Name        string      `yaml:"name"`
	Description string      `yaml:"description"`
	Flags       []*flag     `yaml:"flags"`
	Args        []*argument `yaml:"args"`
	Subcommands []*Command  `yaml:"subcommands"`

	CobraCounterpart *cobra.Command // holds a reference to the created cobra command which is needed
	// to generate the subcommands only when completion code is being created.
}

// flag represents a flag option on a command
type flag struct {
	Name        string `yaml:"name"`
	Shorthand   string `yaml:"shorthand"`
	Description string `yaml:"description"`
	Type        string `yaml:"type"`
}

// source is the type and address of the plugin.
type source struct {
	Type string `yaml:"type"`
	URL  string `yaml:"url"`
}

// argument represents an argument of a subcommand
type argument struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
	Type        string `yaml:"type"`
	// Multiple indicates that this command takes an arbitrary number of arguments of this type. This means
	// that it needs to be only on the last argument in the list.
	// TODO: loading plugins should probably be handled in this package because multiple is something that
	// should be checked on plugin load.
	Mutliple bool `yaml:"multiple"`
}
