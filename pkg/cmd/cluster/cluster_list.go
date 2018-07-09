package cluster

import (
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/clusterlinker"
	"github.com/dcos/dcos-cli/pkg/config"
	"github.com/dcos/dcos-cli/pkg/dcos"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/spf13/cobra"
)

// newCmdClusterList lists the clusters.
func newCmdClusterList(ctx api.Context) *cobra.Command {
	var onlyAttached bool
	var jsonOutput bool
	cmd := &cobra.Command{
		Use:  "list",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			currentCluster, err := ctx.Cluster()
			var currentClusterID string
			if err == nil {
				currentClusterID = currentCluster.ID()
			}

			if onlyAttached && currentCluster == nil {
				return errors.New("no cluster is attached. Please run `dcos cluster attach <cluster-name>`")
			}

			clusters := make(chan *config.Cluster)
			go func() {
				if onlyAttached {
					clusters <- currentCluster
				} else {
					clusterIDs := make(map[string]bool)
					for _, cluster := range ctx.Clusters() {
						clusters <- cluster
						clusterIDs[cluster.ID()] = true
					}

					if currentCluster != nil {
						attachedClient := clusterlinker.NewClient(ctx.HTTPClient(currentCluster), ctx.Logger())
						linkedClusters, err := attachedClient.Links()
						if err != nil {
							ctx.Logger().Info(err)
						} else {
							for _, linkedCluster := range linkedClusters {
								if _, found := clusterIDs[linkedCluster.ID]; !found {
									cluster := config.NewCluster(nil)
									cluster.SetID(linkedCluster.ID)
									cluster.SetName(linkedCluster.Name)
									cluster.SetURL(linkedCluster.URL)
									clusters <- cluster
								}
							}
						}
					}
				}
				close(clusters)
			}()

			// ClusterInfo contains information about a cluster, it represents an item in the list.
			type ClusterInfo struct {
				Attached bool   `json:"attached"`
				ID       string `json:"id"`
				Name     string `json:"name"`
				Status   string `json:"status"`
				URL      string `json:"url"`
				Version  string `json:"version"`
			}

			var items []ClusterInfo
			var mu sync.Mutex

			var wg sync.WaitGroup
			for cluster := range clusters {
				wg.Add(1)
				go func(cluster *config.Cluster) {
					defer wg.Done()
					item := ClusterInfo{
						ID:       cluster.ID(),
						Name:     cluster.Name(),
						URL:      cluster.URL(),
						Status:   "UNAVAILABLE",
						Version:  "UNKNOWN",
						Attached: (cluster.ID() == currentClusterID),
					}

					httpClient := ctx.HTTPClient(cluster, httpclient.Timeout(3*time.Second))
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

					// Order clusters by name, this guarantees a stable list in table output.
					for i := range items {
						if items[i].Name > item.Name {
							items = append(items[:i], append([]ClusterInfo{item}, items[i:]...)...)
							return
						}
					}
					items = append(items, item)
				}(cluster)
			}
			wg.Wait()

			if jsonOutput {
				out, err := json.MarshalIndent(items, "", "\t")
				if err != nil {
					return err
				}
				fmt.Fprintln(ctx.Out(), string(out))
			} else {
				table := cli.NewTable(ctx.Out(), []string{"", "NAME", "ID", "STATUS", "VERSION", "URL"})
				for _, item := range items {
					var attached string
					if item.Attached {
						attached = "*"
					}
					table.Append([]string{attached, item.Name, item.ID, item.Status, item.Version, item.URL})
				}
				table.Render()
			}
			return nil
		},
	}
	cmd.Flags().BoolVar(&onlyAttached, "attached", false, "returns attached cluster only")
	cmd.Flags().BoolVar(&jsonOutput, "json", false, "returns clusters in json format")
	return cmd
}
