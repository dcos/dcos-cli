package prompt

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"reflect"
	"strconv"

	"golang.org/x/crypto/ssh/terminal"
)

// Prompt prompts for interactive questions.
type Prompt struct {
	in  io.Reader
	out io.Writer
}

// New returns a new prompt.
func New(input io.Reader, output io.Writer) *Prompt {
	return &Prompt{
		in:  input,
		out: output,
	}
}

// Input prompts for a string input.
func (prompt *Prompt) Input(msg string) string {
	fmt.Fprint(prompt.out, msg)
	scanner := bufio.NewScanner(prompt.in)
	scanner.Scan()

	return scanner.Text()
}

// Password prompts for a password. It is similar to input, except that it doesn't echo back to the terminal.
func (prompt *Prompt) Password(msg string) string {
	f, ok := prompt.in.(*os.File)
	if !ok || !terminal.IsTerminal(int(f.Fd())) {
		return prompt.Input(msg)
	}

	fmt.Fprint(prompt.out, msg)
	defer fmt.Fprint(prompt.out, "\n")

	pass, _ := terminal.ReadPassword(int(f.Fd()))
	return string(pass)
}

// Select allows to pick an item from a list of choices. For example :
//
//  Please choose a login provider for your linked cluster:
//  (1) dcos-uid-password
//  (2) saml-sp-initiated
//  (1-2): [...]
func (prompt *Prompt) Select(msg string, choices interface{}) (int, error) {
	rType := reflect.TypeOf(choices)
	if rType.Kind() != reflect.Slice {
		return 0, fmt.Errorf("expected a slice, got %s", rType.Kind())
	}
	rVal := reflect.ValueOf(choices)

	fmt.Fprintln(prompt.out, msg)

	choicesLen := rVal.Len()
	for i := 0; i < choicesLen; i++ {
		fmt.Fprintf(prompt.out, "(%d) %v\n", i+1, rVal.Index(i).Interface())
	}

	choice := prompt.Input(fmt.Sprintf("(%d-%d): ", 1, choicesLen))
	i, err := strconv.Atoi(choice)
	if err != nil {
		return 0, fmt.Errorf("unable to parse selected input: %s", err)
	}
	if i < 1 || i > choicesLen {
		return 0, fmt.Errorf("choice %d doesn't exist", i)
	}
	return i - 1, nil
}

// Confirm prompts for a confirmation, it accepts "yes/no" answers:
//   - "y", "yes", "Y", "Yes"
//   - "n", "no", "N", "No"
//
// defaultChoice is the default answer to fallback to in case
// no explicit input is provided (eg. user just pressed ENTER).
func (prompt *Prompt) Confirm(msg, defaultChoice string) error {
	reader := bufio.NewReader(prompt.in)

ConfirmLoop:
	for i := 0; i < 3; i++ {
		fmt.Fprintf(prompt.out, "%s", msg)
		line, err := reader.ReadBytes('\n')
		if err != nil {
			break ConfirmLoop
		}

		// Strip the trailing newline and a possible carriage return.
		line = line[:len(line)-1]
		if len(line) > 0 && line[len(line)-1] == '\r' {
			line = line[:len(line)-1]
		}

		// Fallback to the default choice in case of empty input.
		if len(line) == 0 {
			line = []byte(defaultChoice)
		}

		switch string(line) {
		case "y", "yes", "Y", "Yes":
			return nil
		case "n", "no", "N", "No":
			break ConfirmLoop
		}
	}
	return errors.New("couldn't get confirmation")
}
