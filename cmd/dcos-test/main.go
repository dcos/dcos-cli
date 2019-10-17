package main

//go:generate env GOOS=linux go build -o ../../tests/integration/fixtures/plugins/dcos-test/linux/dcos-test ./
//go:generate env GOOS=darwin go build -o ../../tests/integration/fixtures/plugins/dcos-test/darwin/dcos-test ./
//go:generate env GOOS=windows go build -o ../../tests/integration/fixtures/plugins/dcos-test/win32/dcos-test.exe ./

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
)

func main() {
	const test = "test"
	if len(os.Args) == 3 && os.Args[1] == test && os.Args[2] == "--help" {
		fmt.Println("Help usage for dcos-test")
		os.Exit(0)
	}

	if len(os.Args) == 3 && os.Args[1] == test && os.Args[2] == "--info" {
		fmt.Println("Helper for integration tests")
		os.Exit(0)
	}

	if len(os.Args) == 4 && os.Args[1] == test && os.Args[2] == "exit" {
		code, err := strconv.Atoi(os.Args[3])
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			code = 1
		}
		os.Exit(code)
	}

	type Output struct {
		Args []string          `json:"args"`
		Env  map[string]string `json:"env"`
	}

	out := Output{
		Args: os.Args,
		Env:  make(map[string]string),
	}

	for _, e := range os.Environ() {
		pair := strings.SplitN(e, "=", 2)
		out.Env[pair[0]] = pair[1]
	}

	err := json.NewEncoder(os.Stdout).Encode(&out)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
