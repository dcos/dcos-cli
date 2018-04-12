package cli

import (
	"io"

	"github.com/olekukonko/tablewriter"
)

// NewTable returns a simple table to output information.
func NewTable(writer io.Writer, header []string) *tablewriter.Table {
	table := tablewriter.NewWriter(writer)
	table.SetHeader(header)

	// Disable line between header and content.
	table.SetHeaderLine(false)
	table.SetBorder(false)
	table.SetRowSeparator(" ")
	table.SetColumnSeparator("")
	table.SetCenterSeparator(" ")
	// Turn off wrapping because it seems to wrap even if the column is set to be wide enough.
	table.SetAutoWrapText(false)

	return table
}
