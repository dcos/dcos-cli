package cli

import (
	"strings"
)

// GlobalFlags represents the DC/OS CLI global flags.
type GlobalFlags struct {
	Verbosity int
	LogLevel  string
	Debug     bool
	Version   bool
}

// Parse parses the DC/OS CLI global flags, it accepts the following:
//   - `-v`, `-vv`: defines the verbosity level.
//   - `--log-level=[level]` (deprecated): sets the log-level.
//   - `--debug` (deprecated): sets the log-level to "debug".
//   - `--version`: displays the DC/OS CLI and cluster versions.
func (gf *GlobalFlags) Parse(args []string) []string {
	var i int
ParseLoop:
	for argsLen := len(args); i < argsLen; i++ {
		switch args[i] {
		case "-v":
			gf.Verbosity = 1
		case "-vv", "-vvv":
			gf.Verbosity = 2
		case "--version":
			gf.Version = true
		case "--debug":
			gf.Debug = true
		case "--log-level":
			if len(args) >= i+2 {
				gf.LogLevel = args[i+1]
				i++
			}
		default:
			if strings.HasPrefix(args[i], "--log-level=") {
				gf.LogLevel = strings.TrimPrefix(args[i], "--log-level=")
			} else {
				break ParseLoop
			}
		}
	}
	return args[i:]
}
