package open

import (
	"os/exec"
)

// Open opens a resource on Windows through the FileProtocolHandler entrypoint of the url DLL.
func (o *OsOpener) Open(resource string) error {
	cmd := exec.Command("rundll32", "url.dll,FileProtocolHandler", resource)
	out, err := cmd.CombinedOutput()
	if len(out) > 0 {
		o.logger.Debug(string(out))
	}
	return err
}
