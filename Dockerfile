FROM golang:1.10.0

RUN go get -u \
    github.com/golang/dep/cmd/dep \
    github.com/golang/lint/golint
