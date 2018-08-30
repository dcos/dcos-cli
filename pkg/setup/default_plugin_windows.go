//+build withbundle

package setup

//go:generate go-bindata -pkg setup -o bundled_plugins.gen.go -ignore=\.gitignore -nometadata -tags "withbundle" -prefix "bundled_plugins" bundled_plugins/windows/
