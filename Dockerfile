FROM golang:1.15

RUN go get -u \
    golang.org/x/lint/golint \
    github.com/awalterschulze/goderive \
    github.com/br-lewis/go-bindata/...

RUN curl -sfL https://install.goreleaser.com/github.com/golangci/golangci-lint.sh | sh -s -- -b $(go env GOPATH)/bin v1.30.0