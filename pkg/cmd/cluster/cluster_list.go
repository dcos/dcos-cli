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

func newSubCmdClusterList(ctx *cli.Context) subcommand.SubCommand {
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
			clusters := ctx.Clusters()

			currentCluster, err := ctx.Cluster()
			var currentClusterID string
			if err == nil {
				currentClusterID = currentCluster.ID()
			}

			// infos is composed of clusters information: attachment, name, id, status, version, and url.
			infos := []clusterInfo{}
			var mu sync.Mutex

			var wg sync.WaitGroup
			for _, cluster := range clusters {
				// Add should execute before the statement creating the goroutine.
				wg.Add(1)
				go func(cluster *cli.Cluster) {
					defer wg.Done()

					var info clusterInfo
					info.Name = cluster.Name()
					info.ID = cluster.ID()
					if info.ID == currentClusterID {
						info.Attached = true
					} else if onlyAttached {
						return
					}
					info.URL = cluster.URL()
					info.Status = "AVAILABLE"
					info.Version, err = getVersion(ctx, cluster)
					if err != nil {
						info.Status = "UNAVAILABLE"
					}

					mu.Lock()
					infos = append(infos, info)
					mu.Unlock()
				}(cluster)
			}
			wg.Wait()

			if jsonOutput {
				// Re-marshal it into json with indents added in for pretty printing.
				out, err := json.MarshalIndent(infos, "", "\t")
				if err != nil {
					return err
				}
				fmt.Fprintln(ctx.Out(), string(out))
			} else {
				table := cli.NewTable(ctx.Out(), []string{"", "NAME", "ID", "STATUS", "VERSION", "URL"})
				for i := range infos {
					var attached string
					if infos[i].Attached {
						attached = "*"
					}
					table.Append([]string{attached, infos[i].Name, infos[i].ID, infos[i].Status, infos[i].Version, infos[i].URL})
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

// getVersion returns the version of the cluster as a string.
func getVersion(ctx api.Context, cluster *cli.Cluster) (string, error) {
	client := ctx.HTTPClient(cluster, httpclient.Timeout(5*time.Second))
	resp, err := client.Get("/dcos-metadata/dcos-version.json")
	if err != nil {
		return "UNKNOWN", err
	}
	defer resp.Body.Close()

	var version version

	json.NewDecoder(resp.Body).Decode(&version)
	return version.Version, nil
}

type version struct {
	Version         string `json:"version"`
	DCOSImageCommit string `json:"dcos-image-commit"`
	BootstrapID     string `json:"bootstrap-id"`
}

type clusterInfo struct {
	Attached bool   `json:"attached"`
	ID       string `json:"id"`
	Name     string `json:"name"`
	Status   string `json:"status"`
	URL      string `json:"url"`
	Version  string `json:"version"`
}
