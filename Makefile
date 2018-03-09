CURRENT_DIR=$(shell pwd)
BUILD_DIR=$(CURRENT_DIR)/build
PKG_DIR=/go/src/github.com/dcos/dcos-cli
BINARY_NAME=dcos
IMAGE_NAME=golang:1.10.0

windows_EXE=.exe

.PHONY: default
default:
	@make $(shell uname | tr [A-Z] [a-z])

.PHONY: darwin linux windows
darwin linux windows:
	$(call inDocker,env GOOS=$(@) go build -o build/$(@)/$(BINARY_NAME)$($(@)_EXE) ./cmd/dcos)

.PHONY: test
test: vet
	$(call inDocker,go test -cover ./...)

.PHONY: vet
vet:
	$(call inDocker,go vet ./...)

.PHONY: vendor
vendor:
	$(call inDocker,go get -u github.com/golang/dep/... && dep ensure)

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
