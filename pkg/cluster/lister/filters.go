package lister

// Filters are filtering conditions for cluster lists.
type Filters struct {
	AttachedOnly bool
	Status       string
	Linked       bool
}

// Filter is a functional option for list filters.
type Filter func(filters *Filters)

// AttachedOnly filters cluster items to only keep the current one.
func AttachedOnly() Filter {
	return func(filters *Filters) {
		filters.AttachedOnly = true
	}
}

// Status filters cluster items based on the Status field.
func Status(status string) Filter {
	return func(filters *Filters) {
		filters.Status = status
	}
}

// Linked indicates that linked clusters should be added to the list.
func Linked() Filter {
	return func(filters *Filters) {
		filters.Linked = true
	}
}
