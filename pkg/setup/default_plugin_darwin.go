package setup

//go:generate go-bindata -pkg setup -o bundled_plugins.gen.go -ignore=\.gitignore -prefix "bundled_plugins/darwin" bundled_plugins/darwin/
