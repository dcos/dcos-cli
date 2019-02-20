class DcosCli < Formula
  desc "The DC/OS command-line interface"
  homepage "https://docs.mesosphere.com/latest/cli/"
  url "https://github.com/dcos/dcos-cli/archive/0.7.9.tar.gz"
  sha256 "5bf909eee73566631e19f554160540b7d5aa4693d2d8858a057cd86bd2875b78"

  depends_on "go" => :build
  depends_on "go-bindata" => :build
  depends_on "wget" => :build

  def install
    ENV["GOPATH"] = buildpath
    ENV["NO_DOCKER"] = "1"

    ENV["VERSION"] = "0.7.9"
    ENV["GO_BUILD_TAGS"] = "corecli"

    bin_path = buildpath/"src/github.com/dcos/dcos-cli"

    bin_path.install Dir["*"]
    cd bin_path do
      system "make", "core-download"
      system "make", "core-bundle"
      system "make", "darwin"
      bin.install "build/darwin/dcos"
    end
  end

  test do
    run_output = shell_output("#{bin}/dcos --version 2>&1")
    assert_match "dcoscli.version=0.7.9", run_output
  end
end
