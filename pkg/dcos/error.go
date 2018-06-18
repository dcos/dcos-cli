package dcos

type Error struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Code        string `json:"code"`
}

// Error converts an API error to a string.
func (err *Error) Error() string {
	return err.Description
}
