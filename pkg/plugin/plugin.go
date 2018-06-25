package plugin

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

// executable defines what commands are associated with which executable file in the plugin.
type executable struct {
	// Executables are found in the binary directory + the filename.
	// This means all executables in a plugin are in the same place.
	Filename string     `yaml:"filename"`
	Commands []*command `yaml:"commands"`
}

// command is a command living within a plugin binary.
type command struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
}

// source is the type and address of the plugin.
type source struct {
	Type string `yaml:"type"`
	URL  string `yaml:"url"`
}
