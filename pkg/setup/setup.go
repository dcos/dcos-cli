package setup

import (
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/antihax/optional"
	dcosclient "github.com/dcos/client-go/dcos"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/internal/cosmos"
	"github.com/dcos/dcos-cli/pkg/login"
	"github.com/dcos/dcos-cli/pkg/mesos"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/dcos/dcos-cli/pkg/prompt"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/vbauerster/mpb"
)

// Opts are options for a setup.
type Opts struct {
	Fs            afero.Fs
	Errout        io.Writer
	Prompt        *prompt.Prompt
	Logger        *logrus.Logger
	LoginFlow     *login.Flow
	ConfigManager *config.Manager
	PluginManager *plugin.Manager
	EnvLookup     func(key string) (string, bool)
	Deprecated    func(msg string) error
}

// Setup represents a cluster setup.
type Setup struct {
	fs            afero.Fs
	errout        io.Writer
	prompt        *prompt.Prompt
	logger        *logrus.Logger
	loginFlow     *login.Flow
	configManager *config.Manager
	pluginManager *plugin.Manager
	envLookup     func(key string) (string, bool)
	deprecated    func(msg string) error
}

// New creates a new setup.
func New(opts Opts) *Setup {
	return &Setup{
		fs:            opts.Fs,
		errout:        opts.Errout,
		prompt:        opts.Prompt,
		logger:        opts.Logger,
		loginFlow:     opts.LoginFlow,
		configManager: opts.ConfigManager,
		pluginManager: opts.PluginManager,
		envLookup:     opts.EnvLookup,
		deprecated:    opts.Deprecated,
	}
}

// Configure triggers the setup flow.
func (s *Setup) Configure(flags *Flags, clusterURL string, attach bool) (*config.Cluster, error) {
	if err := flags.Resolve(); err != nil {
		return nil, err
	}

	s.logger.Info("Setting up the cluster...")

	// Create a Cluster and an HTTP client with the few information already available.
	cluster := config.NewCluster(nil)
	cluster.SetURL(clusterURL)

	httpOpts := []httpclient.Option{
		httpclient.Timeout(5 * time.Second),
		httpclient.Logger(s.logger),
	}

	for i := 0; i < 2; i++ {
		// When using an HTTPS URL, configure TLS for the HTTP client accordingly.
		if strings.HasPrefix(clusterURL, "https://") {
			tlsConfig, err := s.configureTLS(httpOpts, flags)
			if err != nil {
				return nil, err
			}
			cluster.SetTLS(config.TLS{Insecure: tlsConfig.InsecureSkipVerify})
			httpOpts = append(httpOpts, httpclient.TLS(tlsConfig))
		}

		// Make sure we continue the setup flow with the canonical cluster URL.
		canonicalClusterURL, err := detectCanonicalClusterURL(cluster.URL(), httpOpts)
		if err == nil {
			if canonicalClusterURL != cluster.URL() {
				s.logger.Warnf("Continuing cluster setup with: %s", canonicalClusterURL)
				cluster.SetURL(canonicalClusterURL)
			}
			break
		}

		// Download the DC/OS CA bundle when getting an unknown authority error.
		if s.isX509UnknownAuthorityError(err) && len(flags.caBundle) == 0 {
			flags.caBundle, err = s.downloadDCOSCABundle(clusterURL, httpOpts)
			if err != nil {
				return nil, err
			}
			continue
		}
		return nil, err
	}

	// Login to get the ACS token, unless it is already present as an env var.
	acsToken, _ := s.envLookup("DCOS_CLUSTER_SETUP_ACS_TOKEN")
	if acsToken == "" {
		httpClient := httpclient.New(cluster.URL(), httpOpts...)
		var err error
		acsToken, err = s.loginFlow.Start(flags.loginFlags, httpClient)
		if err == login.ErrAuthDisabled {
			s.logger.Warn("This cluster does not require authenticated requests. Skipping login.")
		} else if err != nil {
			return nil, err
		}
	}
	cluster.SetACSToken(acsToken)
	httpClient := httpclient.New(cluster.URL(), append(httpOpts, httpclient.ACSToken(cluster.ACSToken()))...)

	// Read cluster ID from cluster metadata.
	metadata, err := dcos.NewClient(httpClient).Metadata()
	if err != nil {
		return nil, err
	}

	if flags.name != "" {
		// A custom cluster name has been passed as a flag.
		cluster.SetName(flags.name)
	} else if stateSummary, err := mesos.NewClient(httpClient).StateSummary(); err == nil {
		// Read cluster name from Mesos state summary.
		cluster.SetName(stateSummary.Cluster)
	} else {
		// Fallback to cluster ID as cluster name.
		cluster.SetName(metadata.ClusterID)
	}

	// Create the config for the given cluster.
	err = s.configManager.Save(cluster.Config(), metadata.ClusterID, flags.caBundle)
	if err != nil {
		return nil, err
	}

	if attach {
		err = s.configManager.Attach(cluster.Config())
		if err != nil {
			return nil, err
		}
		s.logger.Infof("You are now attached to cluster %s", cluster.ID())
	}

	// Install default plugins (dcos-core-cli and dcos-enterprise-cli).
	s.pluginManager.SetCluster(cluster)
	if err = s.installDefaultPlugins(httpClient); err != nil {
		return nil, err
	}

	s.logger.Infof("%s is now setup", clusterURL)
	return cluster, nil
}

// detectCanonicalClusterURL returns the URL with the response of the HEAD request.
func detectCanonicalClusterURL(clusterURL string, httpOpts []httpclient.Option) (string, error) {
	httpClient := httpclient.New(clusterURL, httpOpts...)
	req, err := httpClient.NewRequest("HEAD", "/", nil)
	if err != nil {
		return "", err
	}

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", err
	}

	if resp.StatusCode == 200 {
		resp.Request.URL.Host = strings.ToLower(resp.Request.URL.Host)

		return strings.TrimRight(resp.Request.URL.String(), "/"), nil
	}
	return "", fmt.Errorf("couldn't detect a canonical cluster URL")
}

// configureTLS creates the TLS configuration for a given set of flags.
func (s *Setup) configureTLS(httpOpts []httpclient.Option, flags *Flags) (*tls.Config, error) {
	// Return early with an insecure TLS config when `--insecure` is passed.
	if flags.insecure {
		return &tls.Config{InsecureSkipVerify: true}, nil
	}

	// Create a cert pool from the CA bundle PEM. The user is prompted for manual
	// verification of the certificate authority, unless `--no-check` or `--ca-bundle`
	// were explicitly passed.
	var certPool *x509.CertPool
	if len(flags.caBundle) > 0 {
		var err error
		certPool, err = s.decodePEMCerts(flags.caBundle, !flags.noCheck)
		if err != nil {
			return nil, err
		}
	}
	return &tls.Config{RootCAs: certPool}, nil
}

// isX509UnknownAuthorityError checks whether an error is of type x509.UnknownAuthorityError.
func (s *Setup) isX509UnknownAuthorityError(err error) bool {
	urlErr, ok := err.(*url.Error)
	if !ok {
		return false
	}
	_, ok = urlErr.Err.(x509.UnknownAuthorityError)
	return ok
}

// downloadDCOSCABundle downloads the cluster certificate authority at "/ca/dcos-ca.crt".
func (s *Setup) downloadDCOSCABundle(clusterURL string, httpOpts []httpclient.Option) ([]byte, error) {
	insecureHTTPClient := httpclient.New(clusterURL, append(httpOpts, httpclient.TLS(&tls.Config{
		InsecureSkipVerify: true,
	}))...)

	resp, err := insecureHTTPClient.Get("/ca/dcos-ca.crt")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	caPEM, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	return caPEM, nil
}

// decodePEMCerts creates a x509.CertPool struct based on a PEM certificate authority bundle.
// When prompt is set to true, the first certificate in the bundle is prompted for user confirmation.
func (s *Setup) decodePEMCerts(caPEM []byte, prompt bool) (*x509.CertPool, error) {
	var certPool *x509.CertPool
	for len(caPEM) > 0 {
		var block *pem.Block
		block, caPEM = pem.Decode(caPEM)
		if block == nil {
			break
		}
		if block.Type != "CERTIFICATE" || len(block.Headers) != 0 {
			continue
		}

		cert, err := x509.ParseCertificate(block.Bytes)
		if err != nil {
			continue
		}

		if certPool == nil {
			certPool = x509.NewCertPool()
			if prompt {
				if err := s.promptCA(cert); err != nil {
					return nil, err
				}
			}
		}
		certPool.AddCert(cert)
	}
	return certPool, nil
}

// installDefaultPlugins installs the dcos-core-cli and (if applicable) the dcos-enterprise-cli plugin.
// The installation of the core plugin only works with DC/OS >= 1.10 and the installation of the EE plugin only works
// with DC/OS >= 1.12 due to the lack of a "Variant" key in the "/dcos-metadata/dcos-version.json" endpoint before.
func (s *Setup) installDefaultPlugins(httpClient *httpclient.Client) error {
	version, err := dcos.NewClient(httpClient).Version()
	if err != nil {
		return fmt.Errorf("unable to get DC/OS version, installation of the plugins aborted: %s", err)
	}

	if regexp.MustCompile(`^1\.[7-9]\D*`).MatchString(version.Version) {
		return errors.New("DC/OS version of the cluster < 1.10, installation of the plugins aborted")
	}

	var wg sync.WaitGroup
	pbar := mpb.New(mpb.WithOutput(s.errout), mpb.WithWaitGroup(&wg))
	wg.Add(2)

	// Install plugins for currently installed packages.
	go func() {
		s.installPackageServicesPlugins(&wg, httpClient, pbar)
		wg.Done()
	}()

	// Install dcos-enterprise-cli.
	go func() {
		// Install dcos-enterprise-cli if the DC/OS variant metadata is "enterprise".
		if version.DCOSVariant == "enterprise" {
			if err := s.installPlugin("dcos-enterprise-cli", httpClient, version, pbar); err != nil {
				s.logger.Debug(err)
			}
		} else if version.DCOSVariant == "" {
			// We add this message if the DC/OS variant is "" (DC/OS < 1.12)
			// or if there was an error while installing the EE plugin.
			s.logger.Error("Please run “dcos package install dcos-enterprise-cli” if you use a DC/OS Enterprise cluster")
		}
		wg.Done()
	}()

	// Install dcos-core-cli.
	errCore := s.installPlugin("dcos-core-cli", httpClient, version, pbar)
	pbar.Wait()
	if errCore != nil {
		return errCore
	}

	var newCommands []string
	for _, installedPlugin := range s.pluginManager.Plugins() {
		for _, command := range installedPlugin.Commands {
			newCommands = append(newCommands, command.Name)
		}
	}

	sort.Strings(newCommands)
	fmt.Fprintf(s.errout, "New commands available: %s\n", strings.Join(newCommands, ", "))
	return nil
}

// installPackageServicesPlugins installs CLI plugins for the services currently installed on the cluster.
// When different versions of the same package are installed, it installs the plugin for the highest version.
func (s *Setup) installPackageServicesPlugins(wg *sync.WaitGroup, httpClient *httpclient.Client, pbar *mpb.Progress) {
	// Install all package CLIs when the env var is present.
	installPackageCLIs, _ := s.envLookup("DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS")
	if installPackageCLIs == "" {
		return
	}

	cosmosClient, err := cosmos.NewClient()
	if err != nil {
		s.logger.Debug(err)
		return
	}

	pkgMap := make(map[string]dcosclient.CosmosPackage)
	result, _, err := cosmosClient.PackageList(context.TODO(), &dcosclient.PackageListOpts{
		CosmosPackageListV1Request: optional.NewInterface(dcosclient.CosmosPackageListV1Request{}),
	})
	if err != nil {
		s.logger.Debug(err)
		return
	}

	for _, pkg := range result.Packages {
		pkgDefinition := pkg.PackageInformation.PackageDefinition

		currentPkg, ok := pkgMap[pkgDefinition.Name]
		if ok && currentPkg.ReleaseVersion >= pkgDefinition.ReleaseVersion {
			continue
		}
		pkgMap[pkgDefinition.Name] = pkgDefinition
	}

	for _, pkg := range pkgMap {
		wg.Add(1)
		go func(name, version string) {
			err := s.installPluginFromCosmos(name, version, httpClient, pbar)
			if err != nil {
				s.logger.Debug(err)
			}
			wg.Done()
		}(pkg.Name, pkg.Version)
	}
}

// installPlugin installs a plugin by its name.
func (s *Setup) installPlugin(name string, httpClient *httpclient.Client, version *dcos.Version, pbar *mpb.Progress) error {
	s.logger.Infof("Installing %s...", name)

	if skip, _ := s.envLookup("DCOS_CLUSTER_SETUP_SKIP_CANONICAL_URL_INSTALL"); skip != "1" {
		err := s.installPluginFromCanonicalURL(name, version, pbar)
		if err == nil {
			return nil
		}
		s.logger.Debug(err)
	}
	if skip, _ := s.envLookup("DCOS_CLUSTER_SETUP_SKIP_COSMOS_INSTALL"); skip != "1" {
		return s.installPluginFromCosmos(name, "", httpClient, pbar)
	}
	return errors.New("skipping plugin installation from Cosmos (DCOS_CLUSTER_SETUP_SKIP_COSMOS_INSTALL=1)")
}

// installPluginFromCanonicalURL installs a plugin using its canonical URL.
func (s *Setup) installPluginFromCanonicalURL(name string, version *dcos.Version, pbar *mpb.Progress) error {
	domain := "downloads.dcos.io"
	if name == "dcos-enterprise-cli" {
		domain = "downloads.mesosphere.io"
	}
	platform := runtime.GOOS

	matches := regexp.MustCompile(`^(\d+)\.(\d+)\D*`).FindStringSubmatch(version.Version)
	if matches == nil {
		return fmt.Errorf("unable to parse DC/OS version %s", version.Version)
	}
	dcosVersion := matches[1] + "." + matches[2]

	url := fmt.Sprintf(
		"https://%s/cli/releases/plugins/%s/%s/x86-64/%s-%s-patch.latest.zip",
		domain, name, platform, name, dcosVersion,
	)
	httpClient := httpclient.New("")
	req, err := httpClient.NewRequest("HEAD", url, nil, httpclient.FailOnErrStatus(false))
	if err != nil {
		return err
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		return err
	}
	if resp.StatusCode >= 400 && resp.StatusCode < 500 {
		url = fmt.Sprintf(
			"https://%s/cli/testing/plugins/%s/%s/x86-64/%s-%s-patch.x.zip",
			domain, name, platform, name, dcosVersion,
		)
	}
	return s.pluginManager.Install(url, &plugin.InstallOpts{
		Name:        name,
		Update:      true,
		ProgressBar: pbar,
	})
}

// installPluginFromCosmos installs a plugin through Cosmos.
func (s *Setup) installPluginFromCosmos(name string, version string, httpClient *httpclient.Client, pbar *mpb.Progress) error {
	// Get package information from Cosmos.
	cosmosClient, err := cosmos.NewClient()
	if err != nil {
		return err
	}
	pkg, _, err := cosmosClient.PackageDescribe(context.TODO(), &dcosclient.PackageDescribeOpts{
		CosmosPackageDescribeV1Request: optional.NewInterface(dcosclient.CosmosPackageDescribeV1Request{
			PackageName:    name,
			PackageVersion: version,
		}),
	})
	if err != nil {
		return err
	}

	pluginInfo, err := cosmos.CLIPluginInfo(pkg, httpClient.BaseURL())
	if err != nil {
		return err
	}

	var checksum plugin.Checksum
	for _, contentHash := range pluginInfo.ContentHash {
		switch contentHash.Algo {
		case dcosclient.SHA256:
			checksum.Hasher = sha256.New()
			checksum.Value = contentHash.Value
		}
	}
	return s.pluginManager.Install(pluginInfo.Url, &plugin.InstallOpts{
		Name:        pkg.Package.Name,
		Update:      true,
		Checksum:    checksum,
		ProgressBar: pbar,
		PostInstall: func(fs afero.Fs, pluginDir string) error {
			pkgInfoFilepath := filepath.Join(pluginDir, "package.json")
			pkgInfoFile, err := fs.OpenFile(pkgInfoFilepath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
			if err != nil {
				return err
			}
			defer pkgInfoFile.Close()
			return json.NewEncoder(pkgInfoFile).Encode(pkg.Package)
		},
	})
}

// promptCA prompts information about the certificate authority to the user.
// They are then expected to manually confirm that they trust it.
func (s *Setup) promptCA(cert *x509.Certificate) error {
	var fingerprintBuf bytes.Buffer

	for i, val := range sha256.Sum256(cert.Raw) {
		fingerprintBuf.WriteString(fmt.Sprintf("%02X", val))

		if i != sha256.Size-1 {
			fingerprintBuf.WriteString(":")
		}
	}

	msg := `Cluster Certificate Authority:

  Issuer: %s

  Validity:
    From:  %s
    Until: %s

  SHA256 fingerprint: %s

Do you trust it? [y/n] `

	return s.prompt.Confirm(fmt.Sprintf(
		msg,
		cert.Issuer,
		cert.NotBefore,
		cert.NotAfter,
		fingerprintBuf.String(),
	), "")
}
