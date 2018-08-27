package plugin

//go:generate goderive .

import (
	"crypto/tls"
	"fmt"
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
)

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

	// PostInstall is a hook which can be invoked after plugin installation.
	// It is invoked right before the plugin is moved to its final location.
	PostInstall func(fs afero.Fs, pluginDir string) error

	path       string
	stagingDir string
}

// Install installs a plugin from a resource.
func (m *Manager) Install(resource string, installOpts *InstallOpts) (err error) {
	// If it's a remote resource, download it first.
	m.logger.Infof("Installing plugin from %s...", resource)
	if strings.HasPrefix(resource, "https://") || strings.HasPrefix(resource, "http://") {
		installOpts.path, err = m.downloadPlugin(resource)
		if err != nil {
			return err
		}
	} else {
		installOpts.path = resource
	}

	// The staging dir is where the plugin will be constructed
	// before eventually getting moved to its final location.
	installOpts.stagingDir, err = afero.TempDir(m.fs, os.TempDir(), "dcos-cli")
	if err != nil {
		return err
	}

	// Build the plugin into the staging directory.
	err = m.buildPlugin(installOpts)
	if err != nil {
		return err
	}
	return m.installPlugin(installOpts)
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
		m.persistPlugin(plugin, pluginFilePath)
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
	infoCmd, err := exec.Command(cmd.Path, cmd.Name, "--info").Output()
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
func (m *Manager) persistPlugin(plugin *Plugin, path string) {
	pluginTOML, err := toml.Marshal(*plugin)
	if err == nil {
		err = afero.WriteFile(m.fs, path, pluginTOML, 0644)
	}
	if err != nil {
		m.logger.Debug(err)
	}
}

// pluginsDir returns the path to the plugins directory.
func (m *Manager) pluginsDir() string {
	return filepath.Join(m.cluster.Dir(), "subcommands")
}

// downloadPlugin downloads a plugin and returns the path to the temporary file it stored it to.
func (m *Manager) downloadPlugin(url string) (string, error) {
	tmpDir, err := afero.TempDir(m.fs, os.TempDir(), "dcos-cli")
	if err != nil {
		return "", err
	}

	resp, err := m.httpClient(url).Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	downloadedFilePath := filepath.Join(tmpDir, m.downloadFilename(resp))

	if err := fsutil.CopyReader(m.fs, resp.Body, downloadedFilePath, 0644); err != nil {
		return "", err
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
		binPath := filepath.Join(binDir, filepath.Base(installOpts.path))
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

// installPlugin installs a plugin from a staging dir into its final location.
// "update" indicates whether an already existing plugin can be overwritten.
func (m *Manager) installPlugin(installOpts *InstallOpts) error {
	dest := filepath.Join(m.pluginsDir(), installOpts.Name)

	if installOpts.Update {
		if err := m.fs.RemoveAll(dest); err != nil {
			return err
		}
	} else {
		pluginDirExists, err := afero.DirExists(m.fs, dest)
		if err != nil {
			m.logger.Debug(err)
		}
		if pluginDirExists {
			return fmt.Errorf("'%s' is already installed", installOpts.Name)
		}
	}

	if err := m.fs.MkdirAll(filepath.Dir(dest), 0755); err != nil {
		return err
	}

	// Copy the plugin folder to its final location. We don't move it as this causes
	// issues when the system's temp dir and the DC/OS dir are on different devices.
	// See https://groups.google.com/forum/m/#!topic/golang-dev/5w7Jmg_iCJQ.
	return fsutil.CopyDir(m.fs, installOpts.stagingDir, dest)
}

// httpClient returns the appropriate HTTP client for a given resource.
func (m *Manager) httpClient(url string) *httpclient.Client {
	httpOpts := []httpclient.Option{
		httpclient.Logger(m.logger),
		httpclient.FailOnErrStatus(true),
	}
	if strings.HasPrefix(url, m.cluster.URL()) {
		httpOpts = append(
			httpOpts,
			httpclient.ACSToken(m.cluster.ACSToken()),
			httpclient.TLS(&tls.Config{
				InsecureSkipVerify: m.cluster.TLS().Insecure,
				RootCAs:            m.cluster.TLS().RootCAs,
			}),
		)
	}
	return httpclient.New("", httpOpts...)
}
