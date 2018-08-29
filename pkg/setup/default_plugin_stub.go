//+build !withbundle

package setup

//go:generate go-bindata -pkg setup -o bundled_plugins_linux.gen.go -ignore=\.gitignore -nometadata -dev -prefix "bundled_plugins" bundled_plugins/linux/
//go:generate go-bindata -pkg setup -o bundled_plugins_darwin.gen.go -ignore=\.gitignore -nometadata -dev -prefix "bundled_plugins" bundled_plugins/darwin/
//go:generate go-bindata -pkg setup -o bundled_plugins_windows.gen.go -ignore=\.gitignore -nometadata -dev -prefix "bundled_plugins" bundled_plugins/windows/
