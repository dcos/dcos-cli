CURRENT_DIR=$(shell pwd)
BUILD_DIR=$(CURRENT_DIR)/build
PKG_DIR=/go/src/github.com/dcos/dcos-cli
BINARY_NAME=dcos
IMAGE_NAME=dcos/dcos-cli

windows_EXE=.exe

.PHONY: default
default:
	@make $(shell uname | tr [A-Z] [a-z])

.PHONY: darwin linux windows
darwin linux windows: docker-image
	$(call inDocker,env GOOS=$(@) go build -o build/$(@)/$(BINARY_NAME)$($(@)_EXE) ./cmd/dcos)

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

.PHONY: vendor
vendor: docker-image
	$(call inDocker,dep ensure)

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
