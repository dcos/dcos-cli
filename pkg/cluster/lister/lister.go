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

const (
	// StatusAvailable refers to a reachable cluster.
	StatusAvailable = "AVAILABLE"

	// StatusUnavailable refers to an unreachable cluster.
	StatusUnavailable = "UNAVAILABLE"

	// StatusUnconfigured refers to an unconfigured cluster (a linked cluster).
	StatusUnconfigured = "UNCONFIGURED"
)

// Item represents a cluster item in the list.
type Item struct {
	Attached bool   `json:"attached"`
	ID       string `json:"cluster_id"`
	Name     string `json:"name"`
	Status   string `json:"status"`
	URL      string `json:"url"`
	Version  string `json:"version"`
	cluster  *config.Cluster
}

// Cluster returns the cluster associated to the item.
func (i *Item) Cluster() *config.Cluster {
	return i.cluster
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
		lister.linker = linker.New(lister.httpClient(lister.currentCluster), nil)
	}
	return lister
}

// List retrieves all known clusters.
func (l *Lister) List(filters ...Filter) []*Item {
	items := []*Item{}

	listFilters := Filters{}
	for _, filter := range filters {
		filter(&listFilters)
	}

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

		if listFilters.Linked && l.linker != nil {
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
				Status:  StatusUnavailable,
				Version: "UNKNOWN",
				cluster: cluster,
			}
			if l.currentCluster != nil {
				item.Attached = (cluster.Config().Path() == l.currentCluster.Config().Path())
			}

			if listFilters.AttachedOnly && !item.Attached {
				return
			}

			httpClient := l.httpClient(cluster)
			version, err := dcos.NewClient(httpClient).Version()
			if err == nil {
				item.Status = StatusAvailable
				item.Version = version.Version
			}

			if cluster.Config().Path() == "" {
				item.Status = StatusUnconfigured
			}

			if listFilters.Status != "" && item.Status != listFilters.Status {
				return
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
	return items
}

func (l *Lister) httpClient(cluster *config.Cluster) *httpclient.Client {
	return httpclient.New(
		cluster.URL(),
		httpclient.Logger(l.logger),
		httpclient.ACSToken(cluster.ACSToken()),
		httpclient.Timeout(3*time.Second),
		httpclient.TLS(&tls.Config{
			InsecureSkipVerify: cluster.TLS().Insecure,
			RootCAs:            cluster.TLS().RootCAs,
		}),
	)
}
