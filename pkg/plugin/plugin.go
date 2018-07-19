package plugin

// Plugin defines an external plugin and its associated data.
type Plugin struct {
	Name     string     `toml:"name"`
	Commands []*Command `toml:"commands"`
}

// Command is a Command living within a plugin binary.
type Command struct {
	Name        string `toml:"name"`
	Path        string `toml:"path"`
	Description string `toml:"description"`
}
