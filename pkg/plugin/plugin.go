package plugin

// Plugin is the structure representation of a `plugin.toml file.
// It also contains JSON tags for the `dcos plugin list --json` command.
type Plugin struct {
	Name     string    `toml:"name" json:"name"`
	Commands []Command `toml:"commands" json:"commands"`
}

// Command represents each item defined in the `commands` key of the `plugin.toml` file.
// It also contains JSON tags for the `dcos plugin list --json` command.
type Command struct {
	Name        string `toml:"name" json:"name"`
	Path        string `toml:"path" json:"path"`
	Description string `toml:"description" json:"description"`
}
