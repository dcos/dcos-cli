package plugin

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
)

// Plugin defines an external plugin and its associated data
type Plugin struct {
	Name        string     `yaml:"name"`
	Description string     `yaml:"description"`
	Version     string     `yaml:"version"`
	Executable  string     `yaml:"executable"`
	Source      source     `yaml:"source"`
	Commands    []*Command `yaml:"commands"`
}

// Command is a command living within a plugin binary
type Command struct {
	Name        string      `yaml:"name"`
	Description string      `yaml:"description"`
	Flags       []*Flag     `yaml:"flags"`
	Args        []*Argument `yaml:"args"`
	Subcommands []*Command  `yaml:"subcommands"`
}

// Flag represents a flag option on a command
type Flag struct {
	Name        string `yaml:"name"`
	Shorthand   string `yaml:"shorthand"`
	Description string `yaml:"description"`
	Type        string `yaml:"type"`
}

type source struct {
	Type string `yaml:"zip"`
	URL  string `yaml:"url"`
}

// Argument represents an argument of a subcommand
type Argument struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
	Type        string `yaml:"type"`
	// Multiple indicates that this command takes an arbitrary number of arguments of this type. This means
	// that it needs to be only on the last argument in the list.
	// TODO: loading plugins should probably be handled in this package because multiple is something that
	// should be checked on plugin load.
	Mutliple bool `yaml:"multiple"`
}

// IntoCommands creates a list of cobra commands from the commands available in the plugin
func (p *Plugin) IntoCommands() []*cobra.Command {
	var commands []*cobra.Command

	for _, c := range p.Commands {
		cmd := c.IntoCommand(p.Executable)

		commands = append(commands, cmd)
	}

	return commands
}

// IntoCommand creates a cobra command used to call this command
func (c *Command) IntoCommand(exe string) *cobra.Command {
	cmd := &cobra.Command{
		Use: c.Name,
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Printf("%s called\n", c.Name)

			b := strings.Builder{}
			b.WriteString(exe)
			b.WriteRune(' ')
			b.WriteString(c.Name)
			for _, a := range args {
				b.WriteRune(' ')
				b.WriteString(a)
			}

			fmt.Printf("would call %s\n", b.String())
			return nil
		},
	}

	/*
		for _, s := range c.Subcommands {
			cmd.AddCommand(s.IntoCommand(exe))
		}
	*/

	return cmd
}
