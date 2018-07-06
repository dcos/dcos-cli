package lister

import (
	"crypto/tls"
	"sync"
	"time"

	"github.com/dcos/dcos-cli/pkg/cluster/linker"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/sirupsen/logrus"
)

// Item represents a cluster item in the list.
type Item struct {
	Attached bool   `json:"attached"`
	ID       string `json:"id"`
	Name     string `json:"name"`
	Status   string `json:"status"`
	URL      string `json:"url"`
	Version  string `json:"version"`
}

// Lister is able to retrieve locally configured clusters as well as linked clusters.
type Lister struct {
	configManager  *config.Manager
	linker         *linker.Linker
	currentCluster *config.Cluster
	logger         *logrus.Logger
}

// New creates a new cluster lister.
func New(configManager *config.Manager, logger *logrus.Logger) *Lister {
	lister := &Lister{
		configManager: configManager,
		logger:        logger,
	}
	if currentConfig, err := configManager.Current(); err == nil {
		lister.currentCluster = config.NewCluster(currentConfig)
		lister.linker = linker.New(httpClient(lister.currentCluster), nil)
	}
	return lister
}

// List retrieves all known clusters.
func (l *Lister) List(attachedOnly bool) (items []*Item) {
	clusters := make(chan *config.Cluster)
	go func() {
		l.logger.Info("Reading configured clusters...")
		configuredClusterIDs := make(map[string]bool)
		configs := l.configManager.All()

		for _, conf := range configs {
			cluster := config.NewCluster(conf)
			clusters <- cluster
			configuredClusterIDs[cluster.ID()] = true
		}

		if !attachedOnly && l.linker != nil {
			l.logger.Info("Fetching linked clusters...")
			links, err := l.linker.Links()
			if err != nil {
				l.logger.Debug(err)
			} else {
				for _, link := range links {
					if _, ok := configuredClusterIDs[link.ID]; !ok {
						clusters <- link.ToCluster()
					}
				}
			}
		}
		close(clusters)
	}()

	var mu sync.Mutex

	var wg sync.WaitGroup
	for cluster := range clusters {
		wg.Add(1)
		go func(cluster *config.Cluster) {
			defer wg.Done()
			item := &Item{
				ID:      cluster.ID(),
				Name:    cluster.Name(),
				URL:     cluster.URL(),
				Status:  "UNAVAILABLE",
				Version: "UNKNOWN",
			}
			if l.currentCluster != nil {
				item.Attached = (cluster.Config().Path() == l.currentCluster.Config().Path())
			}

			if attachedOnly && !item.Attached {
				return
			}

			httpClient := httpClient(cluster)
			version, err := dcos.NewClient(httpClient).Version()
			if err == nil {
				item.Status = "AVAILABLE"
				item.Version = version.Version
			}

			if cluster.Config().Path() == "" {
				item.Status = "UNCONFIGURED"
			}
			mu.Lock()
			defer mu.Unlock()

			// Order clusters by name, this guarantees a stable list.
			for i := range items {
				if items[i].Name > item.Name {
					items = append(items[:i], append([]*Item{item}, items[i:]...)...)
					return
				}
			}
			items = append(items, item)
		}(cluster)
	}
	wg.Wait()
	return
}

func httpClient(cluster *config.Cluster) *httpclient.Client {
	return httpclient.New(
		cluster.URL(),
		httpclient.ACSToken(cluster.ACSToken()),
		httpclient.Timeout(3*time.Second),
		httpclient.TLS(&tls.Config{
			InsecureSkipVerify: cluster.TLS().Insecure,
			RootCAs:            cluster.TLS().RootCAs,
		}),
	)
}
