//+build withbundle

package setup

//go:generate go-bindata -pkg setup -o bundled_plugins.gen.go -ignore=\.gitignore -nometadata -prefix "bundled_plugins" bundled_plugins/windows/
