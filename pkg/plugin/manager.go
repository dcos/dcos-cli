package plugin

//go:generate goderive .

import (
	"crypto/tls"
	"encoding/hex"
	"fmt"
	"hash"
	"io"
	"mime"
	"net/http"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"

	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/fsutil"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/pelletier/go-toml"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/vbauerster/mpb"
	"github.com/vbauerster/mpb/decor"
)

// ExistError indicates that a plugin installation failed because it's already installed.
type ExistError struct {
	error
}

// Manager retrieves the plugins available for the current cluster
// by navigating into the filesystem.
type Manager struct {
	fs      afero.Fs
	logger  *logrus.Logger
	cluster *config.Cluster
}

// NewManager returns a new plugin manager.
func NewManager(fs afero.Fs, logger *logrus.Logger) *Manager {
	return &Manager{
		fs:     fs,
		logger: logger,
	}
}

// InstallOpts are installation options for plugin resources.
type InstallOpts struct {
	// Name specify the name of the plugin.
	Name string

	// Update allows to potentially overwrite an already existing plugin of the same name.
	Update bool

	// Checksum represents a CLI plugin resource content hash.
	Checksum Checksum

	ProgressBar *mpb.Progress

	// PostInstall is a hook which can be invoked after plugin installation.
	// It is invoked right before the plugin is moved to its final location.
	PostInstall func(fs afero.Fs, pluginDir string) error

	path       string
	stagingDir string
}

// Checksum contains the hash function and the checksum we expect from a plugin.
type Checksum struct {
	Hasher hash.Hash
	Value  string
}

// Install installs a plugin from a resource.
func (m *Manager) Install(resource string, installOpts *InstallOpts) (plugin *Plugin, err error) {
	// If it's a remote resource, download it first.
	m.logger.Infof("Installing plugin from %s...", resource)
	if strings.HasPrefix(resource, "https://") || strings.HasPrefix(resource, "http://") {
		installOpts.path, err = m.downloadPlugin(resource, installOpts)
		if err != nil {
			return nil, err
		}
		// Remove the downloaded resource from the temp dir at the end of installation.
		defer m.fs.RemoveAll(filepath.Dir(installOpts.path))
	} else {
		installOpts.path = resource
	}

	if err := m.fs.MkdirAll(m.tempDir(), 0755); err != nil {
		return nil, err
	}

	// The staging dir is where the plugin will be constructed before eventually getting moved to
	// its final location. It relies on a temp directory inside the cluster directory instead of
	// the system's temp directory, otherwise this would cause issues when the system's temp dir
	// and the DC/OS dir are on different devices.
	//
	// See https://groups.google.com/forum/m/#!topic/golang-dev/5w7Jmg_iCJQ.
	installOpts.stagingDir, err = afero.TempDir(m.fs, m.tempDir(), "dcos-cli")
	if err != nil {
		return nil, err
	}
	defer m.fs.RemoveAll(installOpts.stagingDir)

	// Build the plugin into the staging directory.
	err = m.buildPlugin(installOpts)
	if err != nil {
		return nil, err
	}

	// Validate the plugin before installation.
	err = m.validatePlugin(installOpts)
	if err != nil {
		return nil, err
	}
	err = m.installPlugin(installOpts)
	if err != nil {
		return nil, err
	}
	return m.loadPlugin(installOpts.Name)
}

// SetCluster sets the plugin manager's target cluster.
func (m *Manager) SetCluster(cluster *config.Cluster) {
	m.cluster = cluster
}

// Remove removes a plugin from the filesystem.
func (m *Manager) Remove(name string) error {
	pluginDir := filepath.Join(m.pluginsDir(), name)
	pluginDirExists, err := afero.DirExists(m.fs, pluginDir)
	if err != nil {
		return err
	}
	if !pluginDirExists {
		return fmt.Errorf("'%s' is not a plugin directory", pluginDir)
	}
	err = m.fs.RemoveAll(pluginDir)
	if err != nil {
		return err
	}
	m.logger.Infof("Removed %s as a plugin from the CLI", name)
	return nil
}

// Plugins returns the plugins associated with the current cluster.
func (m *Manager) Plugins() (plugins []*Plugin) {
	pluginDirs, err := afero.ReadDir(m.fs, m.pluginsDir())
	if err != nil {
		m.logger.Debugf("Couldn't open plugin dir: %s", err)
		return plugins
	}

	for _, pluginDir := range pluginDirs {
		if !pluginDir.IsDir() {
			continue
		}
		plugin, err := m.loadPlugin(pluginDir.Name())
		if err != nil {
			// We don't want to see the CLI failing if a single plugin is malformed.
			// We thus log the error but continue if there is an issue at that step.
			m.logger.Debugf("Couldn't load plugin: %s", err)
			continue
		}
		plugins = append(plugins, plugin)
	}
	return plugins
}

// Plugin finds a plugin identified by a given name.
func (m *Manager) Plugin(name string) (*Plugin, error) {
	pluginDirs, err := afero.ReadDir(m.fs, m.pluginsDir())
	if err != nil {
		return nil, err
	}
	for _, pluginDir := range pluginDirs {
		if pluginDir.IsDir() && pluginDir.Name() == name {
			return m.loadPlugin(pluginDir.Name())
		}
	}
	return nil, fmt.Errorf("unknown plugin %s", name)
}

// loadPlugin loads a plugin based on its name.
func (m *Manager) loadPlugin(name string) (*Plugin, error) {
	m.logger.Infof("Loading plugin '%s'...", name)

	plugin := &Plugin{Name: name}
	pluginPath := filepath.Join(m.pluginsDir(), name, "env")
	pluginFilePath := filepath.Join(pluginPath, "plugin.toml")

	if err := m.unmarshalPlugin(plugin, pluginFilePath); err != nil {
		return nil, err
	}

	// Save a deep copy of the plugin once it's loaded from the plugin.toml file.
	persistedPlugin := &Plugin{}
	plugin.dir = pluginPath
	deriveDeepCopy(persistedPlugin, plugin)

	if len(plugin.Commands) == 0 {
		plugin.Commands = m.findCommands(pluginPath)
	}

	// Normalize plugin commands by putting binary full paths and description summaries.
	for i, cmd := range plugin.Commands {
		if !filepath.IsAbs(cmd.Path) {
			cmd.Path = filepath.Join(pluginPath, cmd.Path)
		}
		if cmd.Description == "" {
			cmd.Description = m.commandDescription(cmd)
		}
		plugin.Commands[i] = cmd
	}

	// Compare the normalized plugin with the saved copy to know whether or not the file should be updated.
	if !reflect.DeepEqual(persistedPlugin, plugin) {
		if err := m.persistPlugin(plugin, pluginFilePath); err != nil {
			m.logger.Debug(err)
		}
	}
	return plugin, nil
}

// findCommands discovers commands in a given directory according to conventions.
// Each command should be contained in a dedicated binary named `dcos-{command}`.
// On Windows it must have the `.exe`` extension.
func (m *Manager) findCommands(pluginDir string) (commands []Command) {
	binDir := filepath.Join(pluginDir, "bin")
	if runtime.GOOS == "windows" {
		// On Windows we check for the `bin` dir. If it doesn't exist we use the legacy `Scripts` dir.
		binDirExists, err := afero.DirExists(m.fs, binDir)
		if err != nil || !binDirExists {
			binDir = filepath.Join(pluginDir, "Scripts")
		}
	}

	m.logger.Debugf("Discovering commands in '%s'...", binDir)

	binaries, err := afero.ReadDir(m.fs, binDir)
	if err != nil {
		m.logger.Debug(err)
		return nil
	}

	for _, binary := range binaries {
		if !strings.HasPrefix(binary.Name(), "dcos-") {
			continue
		}
		cmd := Command{
			Path: filepath.Join(binDir, binary.Name()),
			Name: strings.TrimPrefix(binary.Name(), "dcos-"),
		}
		if runtime.GOOS == "windows" {
			cmd.Name = strings.TrimSuffix(cmd.Name, ".exe")
		}
		m.logger.Debugf("Discovered '%s' command", cmd.Name)
		commands = append(commands, cmd)
	}
	return commands
}

// commandDescription gets the command info summary by invoking the binary with the `--info` flag.
func (m *Manager) commandDescription(cmd Command) (desc string) {
	infoCmd, err := exec.Command(cmd.Path, cmd.Name, "--info").Output() // nolint: gosec
	if err != nil {
		m.logger.Debugf("Couldn't get info summary for the '%s' command: %s", cmd.Name, err)
	} else {
		desc = strings.TrimSpace(string(infoCmd))
	}
	return desc
}

// unmarshalPlugin unmarshals a `plugin.toml` file into a Plugin structure.
func (m *Manager) unmarshalPlugin(plugin *Plugin, path string) error {
	data, err := afero.ReadFile(m.fs, path)
	if err != nil {
		m.logger.Debugf("Couldn't open plugin.toml: %s", err)
		return nil
	}
	return toml.Unmarshal(data, plugin)
}

// persistPlugin saves a `plugin.toml` file representing the plugin.
func (m *Manager) persistPlugin(plugin *Plugin, path string) error {
	if err := m.fs.MkdirAll(m.tempDir(), 0755); err != nil {
		return err
	}

	f, err := afero.TempFile(m.fs, m.tempDir(), "plugin.toml")
	if err != nil {
		return err
	}

	defer m.fs.Remove(f.Name())
	defer f.Close()

	if err := toml.NewEncoder(f).Encode(*plugin); err != nil {
		return err
	}
	return m.fs.Rename(f.Name(), path)
}

// pluginsDir returns the path to the plugins directory.
func (m *Manager) pluginsDir() string {
	return filepath.Join(m.cluster.Dir(), "subcommands")
}

// tempDir returns the path to the temp directory.
func (m *Manager) tempDir() string {
	return filepath.Join(m.cluster.Dir(), "tmp")
}

// downloadPlugin downloads a plugin and returns the path to the temporary file it stored it to.
func (m *Manager) downloadPlugin(url string, installOpts *InstallOpts) (string, error) {
	tmpDir, err := afero.TempDir(m.fs, os.TempDir(), "dcos-cli")
	if err != nil {
		return "", err
	}

	client, err := m.httpClient(url)
	if err != nil {
		return "", err
	}
	resp, err := client.Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	downloadedFilePath := filepath.Join(tmpDir, m.downloadFilename(resp))

	var respReader io.Reader
	if installOpts.Checksum.Hasher != nil {
		respReader = io.TeeReader(resp.Body, installOpts.Checksum.Hasher)
	} else {
		respReader = resp.Body
	}

	if installOpts.ProgressBar != nil {
		bar := installOpts.ProgressBar.AddBar(
			resp.ContentLength,
			mpb.PrependDecorators(decor.Name(installOpts.Name)),
			mpb.AppendDecorators(
				decor.OnComplete(decor.CountersKibiByte("% 6.1f / % 6.1f"), " plugin is now installed"),
			),
			mpb.BarClearOnComplete(),
		)
		if resp.ContentLength > 0 {
			respReader = bar.ProxyReader(respReader)
		} else {
			respReader = newStreamReader(respReader, bar)
		}
	}

	if err := fsutil.CopyReader(m.fs, respReader, downloadedFilePath, 0644); err != nil {
		return "", err
	}

	if installOpts.Checksum.Hasher != nil {
		m.logger.Debugf("Verifying checksum for %s...", url)
		computedChecksum := hex.EncodeToString(installOpts.Checksum.Hasher.Sum(nil))
		if computedChecksum != installOpts.Checksum.Value {
			return "", fmt.Errorf("computed checksum %s for %s, expected %s", computedChecksum, url, installOpts.Checksum.Value)
		}
	}
	return downloadedFilePath, nil
}

// downloadFilename picks a filename for the resource to download. It first reads the
// `Content-Disposition` header, when not set it defaults to the URL path basename.
func (m *Manager) downloadFilename(resp *http.Response) string {
	contentDisposition := resp.Header.Get("Content-Disposition")
	_, dispositionParams, err := mime.ParseMediaType(contentDisposition)
	if err != nil {
		m.logger.Debug(err)
	} else if filename, ok := dispositionParams["filename"]; ok {
		return filename
	}
	return path.Base(resp.Request.URL.Path)
}

// buildPlugin constructs the plugin structure within a target directory, based on a path to a plugin resource.
func (m *Manager) buildPlugin(installOpts *InstallOpts) error {
	plugin := &Plugin{}

	// Detect the plugin resource media type.
	contentType, err := fsutil.DetectMediaType(m.fs, installOpts.path)
	if err != nil {
		return err
	}

	envDir := filepath.Join(installOpts.stagingDir, "env")

	switch contentType {
	case "application/zip":
		// Unzip the plugin into the staging dir and validate its plugin.toml, if any.
		if err := fsutil.Unzip(m.fs, installOpts.path, envDir); err != nil {
			return err
		}
		pluginFilePath := filepath.Join(envDir, "plugin.toml")
		if err := m.unmarshalPlugin(plugin, pluginFilePath); err != nil {
			return err
		}
		if plugin.Name != "" {
			installOpts.Name = plugin.Name
		}

	// The current media type detection mechanism (based on the stdlib) cannot
	// detect binary executables. Thus, we assume the resource is an actual binary
	// when it's not a ZIP archive.
	default:
		// Copy the binary into the staging dir's bin folder,
		binDir := filepath.Join(envDir, "bin")
		if err := m.fs.MkdirAll(binDir, 0755); err != nil {
			return err
		}
		binaryFilename := filepath.Base(installOpts.path)
		if installOpts.Name != "" {
			binaryFilename = "dcos-" + installOpts.Name
		}
		binPath := filepath.Join(binDir, binaryFilename)
		err := fsutil.CopyFile(m.fs, installOpts.path, binPath, 0751)
		if err != nil {
			return err
		}
	}

	// If there is no plugin name, use the resource file basename.
	if installOpts.Name == "" {
		basename := filepath.Base(installOpts.path)
		installOpts.Name = strings.TrimSuffix(basename, filepath.Ext(basename))
	}
	if installOpts.PostInstall != nil {
		return installOpts.PostInstall(m.fs, installOpts.stagingDir)
	}
	return nil
}

// validatePlugin validates that a plugin is properly structured.
func (m *Manager) validatePlugin(installOpts *InstallOpts) error {
	pluginDir := filepath.Join(installOpts.stagingDir, "env")

	hasPluginTOML, err := afero.Exists(m.fs, filepath.Join(pluginDir, "plugin.toml"))
	if err != nil {
		m.logger.Debugf("Couldn't check if plugin.toml exists: %s", err)
	}

	if !hasPluginTOML && len(m.findCommands(pluginDir)) == 0 {
		return fmt.Errorf("%s has no commands", installOpts.Name)
	}

	// TODO: verify that plugin binaries are executables?
	return nil
}

// installPlugin installs a plugin from a staging dir into its final location.
// "update" indicates whether an already existing plugin can be overwritten.
func (m *Manager) installPlugin(installOpts *InstallOpts) error {
	dest := filepath.Join(m.pluginsDir(), installOpts.Name)

	if err := m.fs.MkdirAll(filepath.Dir(dest), 0755); err != nil {
		return err
	}

	if installOpts.Update {
		if err := m.fs.RemoveAll(dest); err != nil {
			return err
		}
	}

	err := m.fs.Rename(installOpts.stagingDir, dest)
	if err != nil {
		if os.IsExist(err) {
			return ExistError{fmt.Errorf("'%s' is already installed", installOpts.Name)}
		}
	}
	return err
}

// httpClient returns the appropriate HTTP client for a given resource.
func (m *Manager) httpClient(url string) (*httpclient.Client, error) {
	httpOpts := []httpclient.Option{
		httpclient.Logger(m.logger),
		httpclient.FailOnErrStatus(true),
	}
	clusterTLS, err := m.cluster.TLS()
	if err != nil {
		return nil, config.NewSSLError(err)
	}
	if strings.HasPrefix(url, m.cluster.URL()) {
		httpOpts = append(
			httpOpts,
			httpclient.ACSToken(m.cluster.ACSToken()),
			httpclient.TLS(&tls.Config{
				InsecureSkipVerify: clusterTLS.Insecure, // nolint: gosec
				RootCAs:            clusterTLS.RootCAs,
			}),
		)
	}
	return httpclient.New("", httpOpts...), nil
}

// newStreamReader updates the progress bar as it reads from the io.Reader,
// keeping the total 1 byte ahead of the current progress. When io.EOF is returned,
// the extra byte is decremented from the total, triggering a bar completed event.
// It is used to indicate download progress for plugins with unknown Content-Length.
func newStreamReader(r io.Reader, bar *mpb.Bar) *streamReader {
	return &streamReader{r, bar, 1}
}

type streamReader struct {
	io.Reader
	bar   *mpb.Bar
	total int
}

func (sr *streamReader) Read(p []byte) (n int, err error) {
	n, err = sr.Reader.Read(p)
	sr.total += n
	if err == io.EOF {
		sr.total--
	}
	sr.bar.SetTotal(int64(sr.total), false)
	sr.bar.IncrBy(n)
	return
}
