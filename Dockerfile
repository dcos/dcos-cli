FROM golang:1.11

RUN go get -u \
    golang.org/x/lint/golint \
    github.com/awalterschulze/goderive \
    github.com/br-lewis/go-bindata/...

