//+build !withbundle

package setup

//go:generate go-bindata -pkg setup -o bundled_plugins_stub_linux.gen.go -ignore=\.gitignore -nometadata -dev -tags "!withbundle" -prefix "bundled_plugins" bundled_plugins/linux/
//go:generate go-bindata -pkg setup -o bundled_plugins_stub_darwin.gen.go -ignore=\.gitignore -nometadata -dev -tags "!withbundle" -prefix "bundled_plugins" bundled_plugins/darwin/
//go:generate go-bindata -pkg setup -o bundled_plugins_stub_windows.gen.go -ignore=\.gitignore -nometadata -dev -tags "!withbundle" -prefix "bundled_plugins" bundled_plugins/windows/

// This file generates windows, mac, and linux bundles because they each should contain different things
// but they're debug so they don't actually contain the data and instead will point to the correct
// directory.

// To actually use these, the generated files will expect the CLI to run either in this directory or one
// which has `bundled_plugins/<os>/core-<version>.zip`