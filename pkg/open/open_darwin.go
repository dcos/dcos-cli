package open

import (
	"os/exec"
)

// Open opens a resource on macOS, using the "open" command.
func (o *OsOpener) Open(resource string) error {
	cmd := exec.Command("open", resource)
	out, err := cmd.CombinedOutput()
	if len(out) > 0 {
		o.logger.Debug(string(out))
	}
	return err
}
