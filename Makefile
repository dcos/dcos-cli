CURRENT_DIR=$(shell pwd)
PKG=github.com/dcos/dcos-cli
PKG_DIR=/go/src/$(PKG)
IMAGE_NAME=dcos/dcos-cli
VERSION?=$(shell git rev-parse HEAD)

windows_EXE=.exe

.PHONY: default
default:
	@make $(shell uname | tr [A-Z] [a-z])

.PHONY: darwin linux windows
darwin linux windows: docker-image
	$(call inDocker,env GOOS=$(@) go build \
		-ldflags '-X $(PKG)/pkg/cli/version.version=$(VERSION)' \
		-tags '$(GO_BUILD_TAGS)' \
		-o build/$(@)/dcos$($(@)_EXE) ./cmd/dcos)

.PHONY: core-bundle
core-bundle: docker-image
	$(call inDocker,go-bindata -pkg setup -o pkg/setup/corecli_linux.gen.go -nometadata -tags "corecli" -prefix "build/linux" build/linux/core.zip)
	$(call inDocker,go-bindata -pkg setup -o pkg/setup/corecli_darwin.gen.go -nometadata -tags "corecli" -prefix "build/darwin" build/darwin/core.zip)
	$(call inDocker,go-bindata -pkg setup -o pkg/setup/corecli_windows.gen.go -nometadata -tags "corecli" -prefix "build/windows" build/windows/core.zip)

.PHONY: core-download
core-download:
	mkdir -p build/linux build/darwin build/windows
	wget https://downloads.dcos.io/cli/plugins/dcos-core-cli/1.12/linux/x86-64/dcos-core-cli.zip -O build/linux/core.zip
	wget https://downloads.dcos.io/cli/plugins/dcos-core-cli/1.12/darwin/x86-64/dcos-core-cli.zip -O build/darwin/core.zip
	wget https://downloads.dcos.io/cli/plugins/dcos-core-cli/1.12/windows/x86-64/dcos-core-cli.zip -O build/windows/core.zip

.PHONY: test
test: vet
	$(call inDocker,go test -race -cover ./...)

.PHONY: vet
vet: lint
	$(call inDocker,go vet ./...)

.PHONY: lint
lint: docker-image
	# Can be simplified once https://github.com/golang/lint/issues/320 is fixed.
	$(call inDocker,golint -set_exit_status ./cmd/... ./pkg/...)

.PHONY: generate
generate: docker-image
	$(call inDocker,go generate ./...)

.PHONY: vendor
vendor: docker-image
	$(call inDocker,go mod vendor)

.PHONY: docker-image
docker-image:
ifndef NO_DOCKER
	docker build -t $(IMAGE_NAME) .
endif

.PHONY: clean
clean:
	rm -rf build

ifdef NO_DOCKER
  define inDocker
    $1
  endef
else
  define inDocker
    docker run \
      -v $(CURRENT_DIR):$(PKG_DIR) \
      -w $(PKG_DIR) \
      --rm \
      $(IMAGE_NAME) \
    bash -c "$1"
  endef
endif
