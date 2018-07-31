package cluster

import (
	"encoding/json"
	"errors"

	"github.com/dcos/dcos-cli/api"
	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/cluster/lister"
	"github.com/spf13/cobra"
)

// newCmdClusterList lists the clusters.
func newCmdClusterList(ctx api.Context) *cobra.Command {
	var attachedOnly bool
	var jsonOutput bool
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List the clusters configured and the ones linked to the current cluster",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			var filters []lister.Filter
			if attachedOnly {
				filters = append(filters, lister.AttachedOnly())
			} else {
				filters = append(filters, lister.Linked())
			}

			items := lister.New(ctx.ConfigManager(), ctx.Logger()).List(filters...)
			if attachedOnly && len(items) == 0 {
				return errors.New("no cluster is attached. Please run `dcos cluster attach <cluster-name>`")
			}

			if jsonOutput {
				enc := json.NewEncoder(ctx.Out())
				enc.SetIndent("", "    ")
				return enc.Encode(items)
			}

			table := cli.NewTable(ctx.Out(), []string{"", "NAME", "ID", "STATUS", "VERSION", "URL"})
			for _, item := range items {
				var attached string
				if item.Attached {
					attached = "*"
				}
				table.Append([]string{attached, item.Name, item.ID, item.Status, item.Version, item.URL})
			}
			table.Render()

			return nil
		},
	}
	cmd.Flags().BoolVar(&attachedOnly, "attached", false, "returns attached cluster only")
	cmd.Flags().BoolVar(&jsonOutput, "json", false, "returns clusters in json format")
	return cmd
}
