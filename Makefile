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
		-o build/$(@)/dcos$($(@)_EXE) ./cmd/dcos)

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
