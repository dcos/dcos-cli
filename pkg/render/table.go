package render

import (
	"fmt"
	"io"
	"strings"

	"github.com/mattn/go-runewidth"
)

const (
	alignLeft = iota
	alignRight
)

// Table representation for CLI outputs.
type Table struct {
	columns []*column
	rows    [][]interface{}
}

// NewTable returns a new table based on a set of column names.
func NewTable(columns []string) *Table {
	table := &Table{
		columns: make([]*column, len(columns)),
	}

	for i, col := range columns {
		table.columns[i] = &column{
			header:    col,
			alignment: alignLeft,
			size:      runewidth.StringWidth(col),
		}
	}
	return table
}

// Append adds a row to a table.
func (t *Table) Append(row []interface{}) {
	for i, cell := range row {
		col := t.columns[i]
		cellStr := fmt.Sprintf("%v", cell)
		cellSize := runewidth.StringWidth(cellStr)
		if cellSize > col.size {
			col.size = cellSize
		}
		switch cell.(type) {
		case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64, uintptr:
			col.alignment = alignRight
		}
	}
	t.rows = append(t.rows, row)
}

// Render writes a table into an io.Writer.
func (t *Table) Render(w io.Writer) {
	for _, col := range t.columns {
		fmt.Fprintf(w, "%s ", col.pad(col.header))
	}
	fmt.Fprint(w, "\n")

	for _, row := range t.rows {
		for i, cell := range row {
			col := t.columns[i]
			cellStr := fmt.Sprintf("%v", cell)
			fmt.Fprintf(w, "%s ", col.pad(cellStr))
		}
		fmt.Fprint(w, "\n")
	}
}

type column struct {
	header    string
	size      int
	alignment int
}

func (c *column) pad(s string) string {
	gap := c.size - runewidth.StringWidth(s)
	if c.alignment == alignRight {
		return strings.Repeat(" ", gap) + s
	}
	return s + strings.Repeat(" ", gap)
}
