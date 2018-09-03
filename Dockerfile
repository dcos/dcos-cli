FROM golang:1.11.0

RUN go get -u \
    github.com/golang/lint/golint \
    github.com/awalterschulze/goderive \
    github.com/br-lewis/go-bindata/...

