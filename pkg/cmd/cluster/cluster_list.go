package cluster

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/httpclient"
	"github.com/dcos/dcos-cli/pkg/subcommand"
	"github.com/spf13/cobra"
)

func newDcosCmdClusterList(ctx *cli.Context) subcommand.DcosCommand {
	sc := subcommand.NewInternalCommand(newCmdClusterList(ctx))
	return sc
}

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

			var clusters []*cli.Cluster
			if !onlyAttached {
				clusters = ctx.Clusters()
			} else if currentCluster != nil {
				clusters = append(clusters, currentCluster)
			}

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
			for _, cluster := range clusters {
				wg.Add(1)
				go func(cluster *cli.Cluster) {
					defer wg.Done()
					item := ClusterInfo{
						ID:       cluster.ID(),
						Name:     cluster.Name(),
						URL:      cluster.URL(),
						Status:   "UNAVAILABLE",
						Version:  "UNKNOWN",
						Attached: (cluster.ID() == currentClusterID),
					}

					httpClient := ctx.HTTPClient(cluster, httpclient.Timeout(5*time.Second))
					version, err := cli.NewDCOSClient(httpClient).Version()
					if err == nil {
						item.Status = "AVAILABLE"
						item.Version = version.Version
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
