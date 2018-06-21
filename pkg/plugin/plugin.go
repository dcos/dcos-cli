package plugin

import (
	"os/exec"
	"path/filepath"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/spf13/cobra"
)

// Plugin defines an external plugin and its associated data
type Plugin struct {
	Name        string        `yaml:"name"`
	Description string        `yaml:"description"`
	Version     string        `yaml:"version"`
	Source      source        `yaml:"source"`
	Executables []*Executable `yaml:"executables"`

	// Plugin directory in filesystem
	pluginDir string

	// directory containing the plugin's binaries
	binDir string
}

// Executable defines what commands are associated with which executable file in the plugin
type Executable struct {
	// Executables are found from pluginDir + Filename. This means all executables in a plugin are in
	// the same place.
	Filename string     `yaml:"filename"`
	Commands []*Command `yaml:"commands"`
}

// Command is a command living within a plugin binary
type Command struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
}

type source struct {
	Type string `yaml:"type"`
	URL  string `yaml:"url"`
}

// IntoCommands creates a list of cobra commands from the commands available in the plugin
func (p *Plugin) IntoCommands(ctx *cli.Context) []*cobra.Command {
	var commands []*cobra.Command

	for _, e := range p.Executables {
		for _, c := range e.Commands {
			cmd := c.IntoCommand(ctx, p.binDir, e.Filename)

			commands = append(commands, cmd)
		}
	}

	return commands
}

// IntoCommand creates a cobra command used to call this command
func (c *Command) IntoCommand(ctx *cli.Context, dir string, exe string) *cobra.Command {
	cmd := &cobra.Command{
		Use:                c.Name,
		Short:              c.Description,
		DisableFlagParsing: true,
		SilenceUsage:       true, // Silences usage information from the wrapper CLI on error
		SilenceErrors:      true, // Silences error message if called binary returns an error exit code
		RunE: func(cmd *cobra.Command, args []string) error {

			// Need to prepend the arguments with the commands name so the executed command knows
			// which subcommand to execute (e.g. `dcos marathon app` would send `<binary> app` without this).
			argsWithRoot := append([]string{c.Name}, args...)

			shellOut := exec.Command(filepath.Join(dir, exe), argsWithRoot...)

			shellOut.Stdout = ctx.Out()
			shellOut.Stderr = ctx.ErrOut()
			shellOut.Stdin = ctx.Input()

			err := shellOut.Run()
			if err != nil {
				// Because we're silencing errors through cobra, we need to print this separately.
				ctx.Logger().Error(err)
				return err
			}
			return nil
		},
	}

	return cmd
}
