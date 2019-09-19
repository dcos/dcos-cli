package plugin

import (
	"path/filepath"
	"sort"
)

// Plugin is the structure representation of a `plugin.toml file.
// It also contains JSON tags for the `dcos plugin list --json` command.
type Plugin struct {
	Name     string    `toml:"name" json:"name"`
	Commands []Command `toml:"commands" json:"commands"`
	dir      string
}

// Command represents each item defined in the `commands` key of the `plugin.toml` file.
// It also contains JSON tags for the `dcos plugin list --json` command.
type Command struct {
	Name        string `toml:"name" json:"name"`
	Path        string `toml:"path" json:"path"`
	Description string `toml:"description" json:"description"`
}

// Dir gives the path to the plugin's env directory on the filesystem.
func (p *Plugin) Dir() string {
	return p.dir
}

// CompletionDir returns the absolute path to the directory holding the plugin's completion script files
func (p *Plugin) CompletionDir() string {
	return filepath.Join(p.Dir(), "completion")
}

// CommandNames returns the commands available in the plugin as a sorted list of names.
func (p *Plugin) CommandNames() (commands []string) {
	for _, command := range p.Commands {
		commands = append(commands, command.Name)
	}
	sort.Strings(commands)
	return commands
}
