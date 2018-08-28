package setup

//go:generate go-bindata -pkg setup -o bundled_plugins.gen.go -ignore=\.gitignore -prefix "bundled_plugins/linux" bundled_plugins/linux/
