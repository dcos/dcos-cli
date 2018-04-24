FROM golang:1.10.0

RUN go get -u \
    github.com/golang/dep/cmd/dep
#   github.com/golang/lint/golint

# Workaround https://github.com/golang/lint/issues/397
RUN mkdir -p $GOPATH/src/golang.org/x && \
    git clone --dept=1 https://github.com/golang/lint.git $GOPATH/src/golang.org/x/lint && \
    go get -u golang.org/x/lint/golint
