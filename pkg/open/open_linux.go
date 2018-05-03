package open

import (
	"os/exec"
)

// Open opens a resource on Linux, it relies on "xdg-open".
func (o *OsOpener) Open(resource string) error {
	cmd := exec.Command("xdg-open", resource)
	out, err := cmd.CombinedOutput()
	if len(out) > 0 {
		o.logger.Debug(string(out))
	}
	return err
}
